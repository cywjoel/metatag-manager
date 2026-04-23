import argparse
import getpass

from playwright.sync_api import sync_playwright


def save_login_state(login_url, password, storage_state_path="auth.json"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(login_url, wait_until="networkidle")
        page.get_by_label("Enter visitor password").fill(password)
        page.get_by_role("button").click()
        page.wait_for_load_state("networkidle")

        context.storage_state(path=storage_state_path)
        browser.close()


def main():
    parser = argparse.ArgumentParser(
        description="Authenticate against a Vercel password-protected site using Playwright and save session cookies."
    )
    parser.add_argument(
        "login_url",
        help="URL of the Vercel password-protected site (e.g. https://example.vercel.app).",
    )
    parser.add_argument(
        "--password",
        default=None,
        help=(
            "Site password. "
            "If omitted you will be prompted to enter it securely (recommended)."
        ),
    )
    parser.add_argument(
        "--output",
        default="auth.json",
        metavar="FILE",
        help="Destination file for the exported session cookies (default: auth.json).",
    )
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    save_login_state(args.login_url, password, storage_state_path=args.output)


if __name__ == "__main__":
    main()
