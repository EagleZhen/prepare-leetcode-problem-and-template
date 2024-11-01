from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from markdownify import markdownify
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import mdformat
import re


def setup_selenium() -> WebDriver:
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(10)
    return driver


def get_problem_title_in_plaintext(driver: WebDriver) -> str:
    title_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "a.no-underline.truncate.cursor-text"))
    )
    text_content = title_element.text
    return text_content


def get_problem_description_in_markdown(driver: WebDriver) -> str:
    problem_description_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "elfjS"))
    )

    html_content = problem_description_element.get_attribute("outerHTML")
    # The superscript and subscript are not handled properly by markdownify
    html_content = convert_superscript_and_subscript(html_content)

    markdown_content = markdownify(html_content)
    with open("test.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    return markdown_content


def click_expand_icon(driver):
    # Wait for the element to be clickable and then click it
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "svg[data-icon='expand']"))
    ).click()


def get_template_code(driver: WebDriver) -> str:
    # Wait until the codes are loaded
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "view-lines"))
    )

    # Directly get the code content from the Monaco editor
    code_content = driver.execute_script(
        "return monaco.editor.getModels()[0].getValue();"
    )

    return code_content


def scrape_leetcode(driver: WebDriver, url: str) -> dict:
    # Open the webpage
    driver.get(url)

    problem_title = get_problem_title_in_plaintext(driver)
    problem_description_in_markdown = get_problem_description_in_markdown(driver)

    # Click the expand icon to show the code without wrapping
    template_code = get_template_code(driver)

    return {
        "url": url,
        "title": problem_title,
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


def remove_code_block_ending_blank_line(markdown_content: str) -> str:
    '''
    Remove the blank line after a code block in markdown content
    '''
    # Regular expression to find code blocks
    with open("test.md", "w", encoding="utf-8") as f:
        f.write(markdown_content)

    code_block_pattern = re.compile(r'(```.*?```)', re.DOTALL)

    def remove_blank_line_above_closing(match: re.Match) -> str:
        code_block = match.group(1)
        # Remove blank line above the closing ```
        code_block = re.sub(r'\n\n(```)', r'\n\1', code_block)
        return code_block

    # Apply the function to all code blocks
    modified_markdown_content = code_block_pattern.sub(remove_blank_line_above_closing, markdown_content)

    return modified_markdown_content


def create_directory(directory: str) -> None:
    """
    Create a directory if it does not exist
    If the directory exists, do nothing
    """

    if not os.path.exists(directory):
        os.makedirs(directory)


def construct_readme_file(data: dict, directory: str) -> None:
    '''
    Construct the README file for the problem, which includes the title and description in a formatted way
    '''
    description = format_heading(data["description"])
    description = remove_code_block_ending_blank_line(description)

    readme_content = f"# {data["title"]}\n\n{description}"
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

    os.startfile(output_directory)
