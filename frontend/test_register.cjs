const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  const errors = [];
  page.on("console", msg => {
    const text = msg.text();
    if (msg.type() === "error" || msg.type() === "warning") errors.push(msg.type().toUpperCase() + ": " + text);
  });
  page.on("pageerror", err => errors.push("PAGE_ERROR: " + err.message));
  
  await page.goto("http://localhost:5173/login", { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);
  console.log("Title:", await page.title());
  
  // Click "注册" tab to switch to registration form
  const tabs = page.locator("button");
  const tabCount = await tabs.count();
  console.log("Total buttons:", tabCount);
  for (let i = 0; i < tabCount; i++) {
    const text = await tabs.nth(i).textContent();
    console.log("  Button", i, "text:", `"${text}"`);
  }
  
  // Click the "注册" tab button (the second tab button)
  await tabs.nth(1).click();
  await page.waitForTimeout(500);
  
  // Now check inputs
  const inputs = page.locator("input");
  const inputCount = await inputs.count();
  console.log("Inputs after tab switch:", inputCount);
  for (let i = 0; i < inputCount; i++) {
    const ph = await inputs.nth(i).getAttribute("placeholder");
    console.log("  Input", i, "placeholder:", ph);
  }
  
  // Fill registration form
  if (inputCount >= 4) {
    await inputs.nth(0).fill("testuser999");
    await inputs.nth(1).fill("test999@example.com");
    await inputs.nth(2).fill("password123");
    await inputs.nth(3).fill("password123");
    console.log("Filled all registration fields");
  }
  
  await page.waitForTimeout(300);
  
  // Click submit button (the last button with "注册")
  const submitBtn = page.locator("button[type=submit]");
  const submitCount = await submitBtn.count();
  console.log("Submit buttons:", submitCount);
  if (submitCount > 0) {
    await submitBtn.click();
    console.log("Clicked submit");
    await page.waitForTimeout(2000);
  }
  
  console.log("\nAll console messages:");
  errors.forEach(e => console.log("  " + e));
  await page.screenshot({ path: "D:/jay_demo/scr_after.png" });
  await browser.close();
})();
