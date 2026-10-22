import { Page, Locator, expect } from '@playwright/test';

/**
 * Base class cho tất cả Page Objects.
 * Chứa các method dùng chung cho mọi page trong app.
 *
 * Mọi Page Object phải extends class này.
 */
export abstract class BasePage {
  protected page: Page;
  protected url: string;

  constructor(page: Page, url: string = '/') {
    this.page = page;
    this.url = url;
  }

  /**
   * Điều hướng tới page và chờ load xong.
   */
  async goto(): Promise<void> {
    await this.page.goto(this.url);
    await this.waitForReady();
  }

  /**
   * Chờ page sẵn sàng. Override trong subclass nếu cần custom logic.
   */
  async waitForReady(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Lấy URL hiện tại.
   */
  async getCurrentUrl(): Promise<string> {
    return this.page.url();
  }

  /**
   * Chụp screenshot với tên custom (cho debug).
   */
  async takeScreenshot(name: string): Promise<void> {
    await this.page.screenshot({
      path: `screenshots/${name}.png`,
      fullPage: true,
    });
  }

  /**
   * Helper: chờ và verify text trong element.
   */
  protected async expectText(
    locator: Locator,
    expected: string | RegExp
  ): Promise<void> {
    await expect(locator).toHaveText(expected);
  }

  /**
   * Helper: chờ và verify URL hiện tại match pattern.
   */
  protected async expectUrl(pattern: string | RegExp): Promise<void> {
    await expect(this.page).toHaveURL(pattern);
  }

  /**
   * Reload page hiện tại.
   */
  async reload(): Promise<void> {
    await this.page.reload();
    await this.waitForReady();
  }
}
