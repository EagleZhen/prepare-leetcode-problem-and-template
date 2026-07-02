from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from markdownify import markdownify
import json
import os
import subprocess
import sys
from selenium.webdriver.support.ui import WebDriverWait
import mdformat
import re
from urllib.parse import urlparse


def setup_selenium() -> WebDriver:
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.page_load_strategy = "eager"
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    driver.set_script_timeout(20)
    return driver


def get_problem_identifier_from_url(url: str) -> str:
    path_parts = [part for part in urlparse(url).path.split("/") if part]
    if len(path_parts) < 2 or path_parts[0] != "problems":
        raise ValueError(f"Could not find a LeetCode problem identifier in URL: {url}")
    return path_parts[1]


def save_debug_snapshot(driver: WebDriver) -> None:
    with open("leetcode_debug.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)


def wait_until_not_cloudflare(driver: WebDriver) -> None:
    def is_ready(current_driver: WebDriver) -> bool:
        page_text = current_driver.find_element(By.TAG_NAME, "body").text.lower()
        title = current_driver.title.lower()
        cloudflare_markers = [
            "just a moment",
            "performing security verification",
            "verify you are not a bot",
        ]
        return not any(marker in title or marker in page_text for marker in cloudflare_markers)

    WebDriverWait(driver, 45).until(is_ready)


def fetch_question_data_from_browser(driver: WebDriver, problem_identifier: str) -> dict:
    query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionFrontendId
        title
        content
        codeSnippets {
          lang
          langSlug
          code
        }
      }
    }
    """
    result = driver.execute_async_script(
        """
        const [query, problemIdentifier, done] = arguments;
        fetch('/graphql', {
          method: 'POST',
          credentials: 'include',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({ query, variables: { titleSlug: problemIdentifier } })
        })
          .then(async response => done({
            ok: response.ok,
            status: response.status,
            text: await response.text()
          }))
          .catch(error => done({ ok: false, error: String(error) }));
        """,
        query,
        problem_identifier,
    )

    if not result.get("ok"):
        save_debug_snapshot(driver)
        status = result.get("status", "unknown")
        error = result.get("error") or result.get("text", "")
        raise RuntimeError(
            f"LeetCode GraphQL request failed with status {status}: {error[:300]}"
        )

    payload = json.loads(result["text"])
    if payload.get("errors"):
        raise RuntimeError(f"LeetCode GraphQL returned errors: {payload['errors']}")

    question = payload.get("data", {}).get("question")
    if not question:
        raise RuntimeError(f"No question data returned for identifier: {problem_identifier}")

    return question


def get_problem_title(question: dict) -> str:
    frontend_id = question.get("questionFrontendId")
    title = question["title"]
    if frontend_id:
        return f"{frontend_id}. {title}"
    return title


def get_cpp_template_code(code_snippets: list[dict]) -> str:
    for snippet in code_snippets:
        if snippet.get("langSlug") == "cpp":
            return snippet["code"]

    available_languages = ", ".join(
        snippet.get("lang", "unknown") for snippet in code_snippets
    )
    raise RuntimeError(f"Could not find a C++ code snippet. Available languages: {available_languages}")


def scrape_leetcode(driver: WebDriver, url: str) -> dict:
    # Open the webpage
    driver.get(url)
    wait_until_not_cloudflare(driver)

    problem_identifier = get_problem_identifier_from_url(url)
    question = fetch_question_data_from_browser(driver, problem_identifier)

    html_content = convert_superscript_and_subscript(question["content"])
    problem_description_in_markdown = markdownify(html_content)
    template_code = get_cpp_template_code(question["codeSnippets"])

    return {
        "url": url,
        "title": get_problem_title(question),
        "description": problem_description_in_markdown,
        "template": template_code,
    }


def is_heading(line: str) -> bool:
    return (
        line.startswith("**")
        and line.endswith("**")
        and ((line.find("Example") != -1) or (line.find("Constraints") != -1))
    )


def format_heading(markdown_content: str) -> str:
    lines = markdown_content.split("\n")
    modified_lines = []
    for line in lines:
        if is_heading(line):
            line = "## " + line[2:-2]  # remove bold formatting and make it a 2nd level heading
            modified_lines.append(line)
        else:
            modified_lines.append(line)
    modified_markdown_content = "\n".join(modified_lines)
    return modified_markdown_content


def convert_superscript_and_subscript(html_content: str) -> str:
    '''
    Handle things like superscript and subscript in the html content
    '''
    return (
        html_content
        .replace("<sup>", "^")
        .replace("</sup>", "")
        .replace("<sub>", "_")
        .replace("</sub>", "")
    )


def remove_code_block_extra_blank_lines(markdown_content: str) -> str:
    '''
    Remove extra blank lines after opening and before closing code fences
    '''
    # Regular expression to find code blocks
    code_block_pattern = re.compile(r'(```.*?```)', re.DOTALL)

    def remove_extra_blank_lines(match: re.Match) -> str:
        code_block = match.group(1)
        # Remove blank line below the opening ```
        code_block = re.sub(r'(```[^\n]*\n)\n+', r'\1', code_block)
        # Remove blank line above the closing ```
        code_block = re.sub(r'\n\n(```)', r'\n\1', code_block)
        return code_block

    # Apply the function to all code blocks
    modified_markdown_content = code_block_pattern.sub(remove_extra_blank_lines, markdown_content)

    return modified_markdown_content


def create_directory(directory: str) -> None:
    """
    Create a directory if it does not exist
    If the directory exists, do nothing
    """

    if not os.path.exists(directory):
        os.makedirs(directory)


def open_directory(directory: str) -> None:
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Not a directory: {directory}")

    if hasattr(os, "startfile"):
        os.startfile(directory)
        return

    if sys.platform == "darwin":
        subprocess.run(["open", directory], check=True)
        return

    subprocess.run(["xdg-open", directory], check=True)


def construct_readme_file(data: dict, directory: str) -> None:
    '''
    Construct the README file for the problem, which includes the title and description in a formatted way
    '''
    description = format_heading(data["description"])
    description = remove_code_block_extra_blank_lines(description)

    readme_content = f"# [{data["title"]}]({data["url"]})\n\n{description}"
    with open(os.path.join(directory, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    mdformat.file(os.path.join(directory, "README.md"))


def construct_template_file(data: dict, output_directory: str, template_directory: str) -> None:
    template_content = ""

    # Include the header
    with open(os.path.join(template_directory, "header.cpp"), "r", encoding="utf-8") as f_header:
        template_content += f_header.read() + "\n"

    # Include the Solution class
    template_content += data["template"]

    # Include the main function
    with open(os.path.join(template_directory, "footer.cpp"), "r", encoding="utf-8") as f_footer:
        template_content += "\n\n" + f_footer.read()

    # Write the combined template content to a file
    with open(os.path.join(output_directory, f"{data["title"]}.cpp"), "w", encoding="utf-8") as f:
        f.write(template_content)


if __name__ == "__main__":
    url = input("Enter the URL of the LeetCode problem: ")
    outer_output_directory = input("Enter the directory where you want to save the problem: ")

    # Scrape the data from the LeetCode problem
    driver = setup_selenium()
    data = scrape_leetcode(driver, url)

    # Create the output directory
    output_directory = os.path.join(outer_output_directory, data["title"])
    create_directory(output_directory)

    # Construct the README file
    construct_readme_file(data, output_directory)

    # Construct the template codes
    template_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    construct_template_file(data, output_directory, template_directory)

    driver.quit()

    open_directory(output_directory)
