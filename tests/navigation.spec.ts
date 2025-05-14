import { test, expect } from '@playwright/test';

test.describe('DynamicPathNavigation', () => {
  test('Test navigation to single and multi-level paths and verify content display.', async ({ page }) => {
    // Navigate to a single-level path
    await page.goto('http://localhost:3006/about');
    await expect(page.getByText('Content for path: about')).toBeVisible();

    // Navigate to a multi-level path
    await page.goto('http://localhost:3006/products/item1/details');
    await expect(page.getByText('Content for path: products/item1/details')).toBeVisible();
  });
}); 