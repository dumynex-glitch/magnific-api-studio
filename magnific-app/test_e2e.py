"""
Playwright end-to-end test for Magnific API Studio.
Tests: model selection, file upload, generate submission, and live log panel.
"""
import sys
import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://localhost:8000"
IMAGE_FILE = Path("/home/debian/magnific/image.png")
VIDEO_FILE = Path("/home/debian/magnific/video.mp4")


def test_full_workflow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Collect console messages
        console_msgs = []
        page.on("console", lambda msg: console_msgs.append(msg.text))
        page.on("pageerror", lambda err: console_msgs.append(f"PAGE ERROR: {err}"))

        print("=" * 60)
        print("1. Loading app...")
        page.goto(BASE_URL, timeout=15000)
        expect(page).to_have_title("Magnific API Studio")
        print(f"   Title: {page.title()}")
        print("   PASS")

        print("\n2. Selecting category: Video Generation...")
        page.select_option("#category-select", "video")
        expect(page.locator("#model-select")).to_be_enabled()
        print("   PASS")

        print("\n3. Selecting model: Kling 2.6 Motion Control (Std)...")
        page.select_option("#model-select", "kling-v2-6-motion-control-std")
        page.wait_for_timeout(1000)

        # Wait for form to render
        form = page.locator("#generate-form")
        expect(form).to_be_visible()

        # Verify expected fields exist
        fields = page.locator(".form-group").all()
        field_names = [f.get_attribute("data-field-key") for f in fields]
        print(f"   Form fields: {field_names}")
        assert "image_url" in field_names, f"image_url field missing, got: {field_names}"
        assert "video_url" in field_names, f"video_url field missing, got: {field_names}"
        print("   PASS")

        print("\n4. Switching image_url to Upload File mode...")
        image_toggle = page.locator(".url-file-toggle[data-field='image_url']")
        image_toggle.locator(".toggle-tab[data-mode='file']").click()
        page.wait_for_timeout(300)
        active_tab = image_toggle.locator(".toggle-tab.active").get_attribute("data-mode")
        assert active_tab == "file", f"Expected file mode, got: {active_tab}"
        print("   PASS")

        print("\n5. Switching video_url to Upload File mode...")
        video_toggle = page.locator(".url-file-toggle[data-field='video_url']")
        video_toggle.locator(".toggle-tab[data-mode='file']").click()
        page.wait_for_timeout(300)
        active_tab = video_toggle.locator(".toggle-tab.active").get_attribute("data-mode")
        assert active_tab == "file", f"Expected file mode, got: {active_tab}"
        print("   PASS")

        print("\n6. Uploading image.png...")
        assert IMAGE_FILE.exists(), f"Image file not found: {IMAGE_FILE}"
        file_input = image_toggle.locator("input[type='file']")
        file_input.set_input_files(str(IMAGE_FILE))
        page.wait_for_timeout(500)
        print(f"   Uploaded: {IMAGE_FILE.name} ({IMAGE_FILE.stat().st_size} bytes)")
        print("   PASS")

        print("\n7. Uploading video.mp4...")
        assert VIDEO_FILE.exists(), f"Video file not found: {VIDEO_FILE}"
        file_input = video_toggle.locator("input[type='file']")
        file_input.set_input_files(str(VIDEO_FILE))
        page.wait_for_timeout(500)
        print(f"   Uploaded: {VIDEO_FILE.name} ({VIDEO_FILE.stat().st_size} bytes)")
        print("   PASS")

        print("\n8. Clicking Generate...")
        submit_btn = page.locator("#submit-btn")
        expect(submit_btn).to_be_visible()
        submit_btn.click()
        page.wait_for_timeout(2000)

        # Check button state changed
        btn_text = submit_btn.text_content()
        print(f"   Button text after click: {btn_text}")
        print("   PASS")

        print("\n9. Waiting for logs to appear in UI...")
        # Wait for log panel to receive entries
        page.wait_for_timeout(3000)

        log_count_el = page.locator("#log-count")
        log_count_text = log_count_el.text_content().strip()
        print(f"   Log count badge: {log_count_text}")

        # Check log entries container
        log_entries = page.locator("#log-entries .log-entry")
        entry_count = log_entries.count()
        print(f"   Log entries rendered: {entry_count}")

        if entry_count > 0:
            print("\n10. Log entries content:")
            for i in range(entry_count):
                entry = log_entries.nth(i)
                level = entry.locator(".log-entry-level").text_content().strip()
                category = entry.locator(".log-entry-category").text_content().strip()
                message = entry.locator(".log-entry-message").text_content().strip()
                print(f"    [{level:7s}] {category:15s} {message[:100]}")

        # Verify key log entries
        all_log_text = "\n".join([
            e.locator(".log-entry-message").text_content()
            for e in log_entries.all()
        ])

        checks = {
            "Generate request received": "Generate request received" in all_log_text,
            "File upload logged": "Uploaded" in all_log_text and "file(s)" in all_log_text,
            "Image filename in log": "image.png" in all_log_text or "image_url" in all_log_text,
            "Video filename in log": "video.mp4" in all_log_text or "video_url" in all_log_text,
            "API call logged": "Calling Magnific API" in all_log_text,
        }

        print("\n11. Verification results:")
        all_pass = True
        for check_name, result in checks.items():
            status = "PASS" if result else "FAIL"
            if not result:
                all_pass = False
            print(f"    {status}: {check_name}")

        print("\n12. Checking for console errors...")
        errors = [m for m in console_msgs if "PAGE ERROR" in m or "error" in m.lower()]
        if errors:
            print(f"    WARN: {len(errors)} console message(s):")
            for e in errors[:5]:
                print(f"      - {e[:120]}")
        else:
            print("    PASS: No console errors")

        print("\n" + "=" * 60)
        if all_pass:
            print("ALL CHECKS PASSED")
        else:
            print("SOME CHECKS FAILED - see details above")
            sys.exit(1)

        browser.close()


if __name__ == "__main__":
    test_full_workflow()
