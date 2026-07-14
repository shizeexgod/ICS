const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:8899';
const OUT = 'C:/Users/User/AppData/Local/Temp/claude/c--Users-User-Desktop-ICS-project/cf0c6e87-ca45-42fa-beb2-27c9e6308bcd/scratchpad';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('pageerror', e => console.log('PAGE ERROR:', e.message));
  page.on('console', m => console.log('BROWSER:', m.text()));

  // ---- 1) pricing grid at wide viewport ----
  await page.goto(TARGET_URL, { waitUntil: 'load' });
  await page.locator('#pricing').scrollIntoViewIfNeeded();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/COLS-1-landing-wide.png` });
  const frameDir = await page.evaluate(() => {
    const frame = document.querySelector('#pricing .plans-panel__frame');
    return getComputedStyle(frame).flexDirection;
  });
  console.log('landing plans-panel__frame flex-direction at 1280px:', frameDir);

  // ---- 2) open cabinet, go to calendar, test date/time pickers ----
  await page.route('**/api/v1/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
  });
  await page.route('**/api/v1/auth/send-code', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, dev_code: '1234' }) });
  });
  await page.route('**/api/v1/auth/verify-code', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      access_token: 't', refresh_token: 'r',
      user: { id: 'u1', email: 'a@example.com', name: 'Тест Тестов', phone: null, company_id: 'c1', role: 'admin' }
    }) });
  });
  await page.route('**/api/v1/company/me', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({
      id: 'c1', name: 'Тест', owner_email: 'a@example.com', phone: null, api_key: 'key',
      plan: { plan: 'trial', trial_ends_at: null, subscription_status: 'active', reminders_used: 0, reminders_period_start: null, pro_price_rub: 1490, is_trial_active: true, can_send_reminders: true }
    }) });
  });

  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.click('#openCabinet');
  await page.waitForTimeout(300);
  await page.click('#choiceLoginBtn');
  await page.waitForTimeout(200);
  await page.fill('#cabinetStepLogin input[name=email]', 'a@example.com');
  await page.click('#cabinetStepLogin button[type=submit]');
  await page.waitForTimeout(500);
  await page.fill('#verifyForm input[name=code]', '1234');
  await page.waitForTimeout(900);

  await page.click('.cabinet-app__nav-btn[data-view="calendar"]');
  await page.waitForTimeout(500);

  // open date picker
  await page.click('#calendarDateTrigger');
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/PICKER-1-date-open.png` });

  // pick day 20 (whatever month is current)
  const dayButtons = await page.locator('#pickerDaysGrid button').all();
  let picked = false;
  for (const btn of dayButtons) {
    const txt = (await btn.textContent()).trim();
    if (txt === '20') { await btn.click(); picked = true; break; }
  }
  console.log('picked day 20?', picked);
  await page.waitForTimeout(300);
  const dateVal = await page.locator('#calendarDate').inputValue();
  const dateTriggerTxt = await page.locator('#calendarDateTriggerText').textContent();
  console.log('date hidden value:', dateVal, '| trigger text:', dateTriggerTxt);

  // open time picker
  await page.evaluate(() => {
    const field = document.getElementById('calendarTimeField');
    const anchor = field.closest('.cabinet__panel');
    console.log('DEBUG anchorRect:', JSON.stringify(anchor.getBoundingClientRect()));
    console.log('DEBUG fieldRect (trigger label):', JSON.stringify(field.getBoundingClientRect()));
    const trig = document.getElementById('calendarTimeTrigger');
    console.log('DEBUG triggerRect:', JSON.stringify(trig.getBoundingClientRect()));
    console.log('DEBUG anchor class:', anchor.className);
    console.log('DEBUG anchor computed transform:', getComputedStyle(anchor).transform);
  });
  await page.click('#calendarTimeTrigger');
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    const panel = document.getElementById('calendarTimePanel');
    console.log('DEBUG panel style top/left:', panel.style.top, panel.style.left);
    console.log('DEBUG panel rect:', JSON.stringify(panel.getBoundingClientRect()));
  });
  await page.screenshot({ path: `${OUT}/PICKER-2-time-open.png` });
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('#pickerHourList button')].find(b => b.textContent.trim() === '14');
    const rect = btn.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const atPoint = document.elementFromPoint(cx, cy);
    console.log('DEBUG hour btn rect:', JSON.stringify(rect), 'elementFromPoint tag/id:', atPoint?.tagName, atPoint?.id, atPoint?.textContent?.trim());
    console.log('DEBUG hour btn === atPoint?', btn === atPoint);
  });
  await page.click('#pickerHourList button:has-text("14")');
  await page.waitForTimeout(150);
  await page.screenshot({ path: `${OUT}/PICKER-2b-after-hour.png` });
  const panelHiddenAfterHour = await page.evaluate(() => document.getElementById('calendarTimePanel').hidden);
  console.log('time panel hidden after hour click:', panelHiddenAfterHour);
  const minuteBtnVisible = await page.locator('#pickerMinuteList button:has-text("30")').isVisible();
  console.log('minute 30 button visible?', minuteBtnVisible);
  await page.click('#pickerMinuteList button:has-text("30")');
  await page.waitForTimeout(300);
  const timeVal = await page.locator('#calendarTime').inputValue();
  const timeTriggerTxt = await page.locator('#calendarTimeTriggerText').textContent();
  console.log('time hidden value:', timeVal, '| trigger text:', timeTriggerTxt);

  const panelOpenAfterMinute = await page.evaluate(() => !document.getElementById('calendarTimePanel').hidden);
  console.log('time panel still open after minute pick (should be false):', panelOpenAfterMinute);

  await page.screenshot({ path: `${OUT}/PICKER-3-final-form.png` });

  await browser.close();
})();
