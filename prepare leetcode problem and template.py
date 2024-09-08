from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from markdownify import markdownify as md
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
    markdown_content = md(html_content)
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

def construct_template_file(data: dict, output_directory: str, template_directory: str) -> None:
    template_content = ""
    
    # Include the header
    with open(os.path.join(template_directory, "header.cpp"), "r", encoding="utf-8") as f_header:
        template_content += f_header.read()
    
    # Include the Solution class
    template_content += data["template"]
    
    # Include the main function
    with open(os.path.join(template_directory, "footer.cpp"), "r", encoding="utf-8") as f_footer:
        template_content += "\n\n" + f_footer.read()

    # Write the combined template content to a file
    with open(os.path.join(output_directory, f"{data["title"]}.cpp"), "w", encoding="utf-8") as f:
        f.write(template_content)

if __name__ == "__main__":
    driver = setup_selenium()

    url = "https://leetcode.com/problems/robot-collisions/description/"
    data = scrape_leetcode(driver, url)

    output_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output", data["title"])
    create_directory(output_directory)
    construct_readme_file(data, output_directory)
    
    template_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    construct_template_file(data, output_directory, template_directory)

    driver.quit()
