from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from markdownify import markdownify as md
import os


def setup_selenium() -> WebDriver:
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def get_problem_title_in_plaintext(driver: WebDriver) -> str:
    title_element = driver.find_element(
        By.CSS_SELECTOR, "a.no-underline.truncate.cursor-text"
    )
    text_content = title_element.text
    return text_content


def get_problem_description_in_markdown(driver: WebDriver) -> str:
    problem_description_element = driver.find_element(By.CLASS_NAME, "elfjS")
    html_content = problem_description_element.get_attribute("outerHTML")
    markdown_content = md(html_content)
    return markdown_content


def scrape_leetcode_problem(driver: WebDriver, url: str) -> dict:
    # Open the webpage
    driver.get(url)
    driver.implicitly_wait(10)

    problem_title = get_problem_title_in_plaintext(driver)
    # print("Problem Title:", problem_title)

    problem_description_in_markdown = get_problem_description_in_markdown(driver)

    return {
        "url": url,
        "title": problem_title,
        "description": problem_description_in_markdown,
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
            line = "## " + line[2:-2] # remove bold formatting and make it a 2nd level heading
            modified_lines.append(line)
        else:
            modified_lines.append(line)
    modified_markdown_content = "\n".join(modified_lines)
    return modified_markdown_content


def create_directory(directory: str) -> None:
    """
    Create a directory if it does not exist
    If the directory exists, do nothing
    """

    if not os.path.exists(directory):
        os.makedirs(directory)


def construct_readme_file(data: dict, directory: str) -> None:
    readme_content = f"# {data["title"]}\n\n{format_heading(data['description'])}"
    with open(os.path.join(directory, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_content)


if __name__ == "__main__":
    driver = setup_selenium()

    url = "https://leetcode.com/problems/robot-collisions/description/"
    data = scrape_leetcode_problem(driver, url)

    directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", data["title"])
    create_directory(directory)
    construct_readme_file(data, directory)

    driver.quit()
