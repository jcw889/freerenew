const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

// 获取环境变量
const FC_USERNAME = process.env.FC_USERNAME;
const FC_PASSWORD = process.env.FC_PASSWORD;
const FC_MACHINE_ID = process.env.FC_MACHINE_ID;
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID;

// 随机延迟函数
const randomDelay = async (min = 1000, max = 3000) => {
  const delay = Math.floor(Math.random() * (max - min)) + min;
  console.log(`随机延迟 ${delay}ms...`);
  await new Promise(r => setTimeout(r, delay));
};

// 发送Telegram通知
const sendTelegramMessage = async (message) => {
  if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
    console.log('未配置Telegram通知');
    return;
  }
  
  try {
    console.log(`发送Telegram通知: ${message}`);
    const response = await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: TELEGRAM_CHAT_ID,
        text: message,
        parse_mode: 'Markdown'
      })
    });
    
    const result = await response.json();
    console.log('Telegram通知发送结果:', result.ok ? '成功' : '失败');
  } catch (error) {
    console.error('发送Telegram通知时出错:', error.message);
  }
};

// 主函数
(async () => {
  console.log('启动浏览器...');
  const browser = await puppeteer.launch({
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-accelerated-2d-canvas',
      '--disable-gpu',
      '--window-size=1920,1080',
      '--disable-web-security',
    ]
  });
  
  try {
    const page = await browser.newPage();
    
    // 设置视窗大小
    await page.setViewport({ width: 1920, height: 1080 });
    
    // 设置用户代理
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36');
    
    // 绕过WebDriver检测
    await page.evaluateOnNewDocument(() => {
      delete navigator.__proto__.webdriver;
      
      // 添加Chrome浏览器特性
      window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {
          isInstalled: false,
        },
      };
      
      // 添加语言和平台特性
      Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en-US', 'en'],
      });
      
      Object.defineProperty(navigator, 'plugins', {
        get: () => [
          {
            0: {type: 'application/x-google-chrome-pdf'},
            description: 'Portable Document Format',
            filename: 'internal-pdf-viewer',
            length: 1,
            name: 'Chrome PDF Plugin'
          }
        ],
      });
    });
    
    // 监听请求以便调试
    page.on('response', async (response) => {
      const url = response.url();
      if (url.includes('freecloud.ltd')) {
        console.log(`响应 ${response.status()} 来自: ${url}`);
        
        // 保存页面的额外调试信息
        if (response.status() === 403) {
          const headers = response.headers();
          console.log('收到403状态，响应头:', headers);
          if (headers['cf-mitigated']) {
            console.log('cf-mitigated:', headers['cf-mitigated']);
          }
        }
      }
    });
    
    // 截取控制台日志
    page.on('console', msg => console.log('浏览器控制台:', msg.text()));
    
    console.log('访问登录页面...');
    try {
      await page.goto('https://freecloud.ltd/login', { 
        waitUntil: 'networkidle2',
        timeout: 60000 
      });
    } catch (error) {
      console.log('访问登录页面超时或错误:', error.message);
      console.log('尝试继续...');
    }
    
    // 等待页面加载完成，检查是否存在Cloudflare挑战
    console.log('检查是否存在Cloudflare挑战...');
    const isChallengePresent = await page.evaluate(() => {
      return document.body.textContent.includes('Checking your browser') || 
             document.body.textContent.includes('正在检查您的浏览器') ||
             document.title.includes('Cloudflare') ||
             document.querySelector('div[class*="cf-"]') !== null;
    });
    
    if (isChallengePresent) {
      console.log('检测到Cloudflare挑战，等待挑战完成...');
      try {
        await page.waitForFunction(
          () => !document.body.textContent.includes('Checking your browser') && 
                !document.body.textContent.includes('正在检查您的浏览器') && 
                !document.title.includes('Cloudflare'),
          { timeout: 30000 }
        );
        console.log('Cloudflare挑战已通过');
      } catch (error) {
        console.log('等待Cloudflare挑战通过超时:', error.message);
        
        // 保存页面截图和HTML以便调试
        await page.screenshot({ path: 'cloudflare_challenge.png' });
        const pageContent = await page.content();
        console.log('页面内容:', pageContent.substring(0, 500) + '...');
        
        console.log('尝试继续执行...');
      }
    }
    
    // 确认我们已经在登录页面
    console.log('确认已进入登录页面...');
    try {
      await page.waitForSelector('input[name="username"]', { timeout: 10000 });
    } catch (error) {
      console.log('未找到登录表单，尝试手动导航到登录页...');
      try {
        await page.goto('https://freecloud.ltd/login', { waitUntil: 'networkidle2' });
        await page.waitForSelector('input[name="username"]', { timeout: 10000 });
      } catch (retryError) {
        console.log('二次尝试后仍未找到登录表单:', retryError.message);
        
        // 保存页面截图和HTML以便调试
        await page.screenshot({ path: 'login_page_error.png' });
        const html = await page.content();
        console.log('页面HTML片段:', html.substring(0, 500) + '...');
        
        // 发送Telegram通知
        await sendTelegramMessage('❌ 浏览器自动化失败: 无法访问登录页面或找不到登录表单');
        return;
      }
    }
    
    // 随机延迟，模拟人类行为
    await randomDelay();
    
    // 查找并处理数学验证码
    console.log('查找数学验证码...');
    const mathCaptchaElement = await page.$('input[name="math_captcha"]');
    let mathAnswer = '';
    
    if (mathCaptchaElement) {
      console.log('找到数学验证码输入框，尝试解析验证码问题...');
      const placeholder = await page.evaluate(el => el.getAttribute('placeholder'), mathCaptchaElement);
      console.log(`验证码问题: ${placeholder}`);
      
      // 解析数学问题
      const match = placeholder.match(/(\d+)\s*([+\-*/])\s*(\d+)\s*=\s*\?/);
      if (match) {
        const num1 = parseInt(match[1]);
        const operator = match[2];
        const num2 = parseInt(match[3]);
        
        // 计算答案
        if (operator === '+') {
          mathAnswer = num1 + num2;
        } else if (operator === '-') {
          mathAnswer = num1 - num2;
        } else if (operator === '*') {
          mathAnswer = num1 * num2;
        } else if (operator === '/') {
          mathAnswer = Math.floor(num1 / num2);
        }
        
        console.log(`验证码答案: ${mathAnswer}`);
      } else {
        console.log('无法解析数学验证码问题');
      }
    } else {
      console.log('未找到数学验证码输入框');
    }
    
    // 获取CSRF令牌
    const csrfToken = await page.evaluate(() => {
      const tokenInput = document.querySelector('input[name="_token"]');
      return tokenInput ? tokenInput.value : '';
    });
    
    if (csrfToken) {
      console.log(`找到CSRF令牌: ${csrfToken.substring(0, 10)}...`);
    } else {
      console.log('未找到CSRF令牌');
    }
    
    // 填写登录表单
    console.log('填写登录表单...');
    await page.type('input[name="username"]', FC_USERNAME);
    await randomDelay(500, 1500);
    await page.type('input[name="password"]', FC_PASSWORD);
    
    // 如果找到了数学验证码答案，填入
    if (mathAnswer) {
      await randomDelay(500, 1500);
      await page.type('input[name="math_captcha"]', mathAnswer.toString());
    }
    
    // 确保同意条款被选中
    await randomDelay(500, 1000);
    const agreeCheckbox = await page.$('input[name="agree"]');
    if (agreeCheckbox) {
      const isChecked = await page.evaluate(el => el.checked, agreeCheckbox);
      if (!isChecked) {
        await page.click('input[name="agree"]');
      }
    }
    
    // 提交表单
    console.log('提交登录表单...');
    await randomDelay(1000, 2000);
    
    // 点击登录按钮并等待导航完成
    try {
      await Promise.all([
        page.click('button[type="submit"]'),
        page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 60000 })
      ]);
    } catch (error) {
      console.log('等待导航超时，继续执行:', error.message);
    }
    
    // 保存登录后页面的截图
    await page.screenshot({ path: 'after_login.png' });
    
    // 检查是否登录成功
    console.log('检查登录状态...');
    const isLoggedIn = await page.evaluate(() => {
      return document.body.textContent.includes('退出登录') || 
             document.body.textContent.includes('logout') || 
             document.body.textContent.includes('欢迎回来') ||
             document.body.textContent.includes('welcome back');
    });
    
    if (isLoggedIn) {
      console.log('登录成功！');
      
      // 访问服务器列表页面
      console.log('访问服务器列表页面...');
      try {
        await page.goto('https://freecloud.ltd/server/lxc', { 
          waitUntil: 'networkidle2',
          timeout: 30000 
        });
      } catch (error) {
        console.log('访问服务器列表页面超时:', error.message);
      }
      
      // 保存页面内容以便调试
      await page.screenshot({ path: 'server_list_page.png' });
      
      // 查找服务器信息
      console.log(`查找服务器ID: ${FC_MACHINE_ID}...`);
      
      // 获取页面内容
      const pageContent = await page.content();
      
      // 使用正则表达式查找剩余天数
      const regex = new RegExp(`${FC_MACHINE_ID}[\\s\\S]*?([0-9]+)天后`, 'i');
      const match = pageContent.match(regex);
      
      if (match) {
        const daysLeft = parseInt(match[1]);
        console.log(`服务器 ${FC_MACHINE_ID} 剩余 ${daysLeft} 天`);
        
        // 判断是否需要续费
        if (daysLeft < 3) {
          console.log('剩余天数少于3天，需要续费');
          
          // 访问服务器详情页
          console.log('访问服务器详情页...');
          try {
            await page.goto(`https://freecloud.ltd/server/detail/${FC_MACHINE_ID}`, { 
              waitUntil: 'networkidle2',
              timeout: 30000 
            });
          } catch (error) {
            console.log('访问服务器详情页超时:', error.message);
          }
          
          await randomDelay();
          
          // 查找并点击续费按钮
          console.log('查找续费按钮...');
          const renewButtonSelector = await page.evaluate(() => {
            // 查找包含"续费"文本的按钮
            const buttons = Array.from(document.querySelectorAll('button'));
            const renewButton = buttons.find(btn => 
              btn.textContent.includes('续费') || 
              btn.textContent.includes('renew')
            );
            
            if (renewButton) {
              // 如果找到按钮，返回一个可以唯一标识它的选择器
              return renewButton.id ? `#${renewButton.id}` : 
                     renewButton.className ? `.${renewButton.className.split(' ').join('.')}` : 
                     `button:nth-of-type(${Array.from(document.querySelectorAll('button')).indexOf(renewButton) + 1})`;
            }
            return null;
          });
          
          if (renewButtonSelector) {
            console.log(`找到续费按钮: ${renewButtonSelector}`);
            await page.click(renewButtonSelector);
            
            // 等待续费对话框出现
            try {
              await page.waitForFunction(() => {
                return document.body.textContent.includes('续费时长') || 
                       document.body.textContent.includes('Renewal Period');
              }, { timeout: 10000 });
            } catch (error) {
              console.log('等待续费对话框超时:', error.message);
            }
            
            await randomDelay();
            
            // 选择1个月的续费时长
            console.log('选择1个月续费时长...');
            await page.evaluate(() => {
              // 查找并选择1个月选项
              const monthInputs = Array.from(document.querySelectorAll('input[name="month"]'));
              const oneMonthInput = monthInputs.find(input => input.value === '1');
              if (oneMonthInput && !oneMonthInput.checked) {
                oneMonthInput.click();
              }
            });
            
            await randomDelay();
            
            // 查找并点击确认按钮
            console.log('查找确认按钮...');
            const confirmButtonSelector = await page.evaluate(() => {
              // 查找包含"确认"或"确定"文本的按钮
              const buttons = Array.from(document.querySelectorAll('button'));
              const confirmButton = buttons.find(btn => 
                btn.textContent.includes('确认') || 
                btn.textContent.includes('确定') ||
                btn.textContent.includes('Confirm')
              );
              
              if (confirmButton) {
                return confirmButton.id ? `#${confirmButton.id}` : 
                       confirmButton.className ? `.${confirmButton.className.split(' ').join('.')}` : 
                       `button:nth-of-type(${Array.from(document.querySelectorAll('button')).indexOf(confirmButton) + 1})`;
              }
              return null;
            });
            
            if (confirmButtonSelector) {
              console.log(`找到确认按钮: ${confirmButtonSelector}`);
              await page.click(confirmButtonSelector);
              
              // 等待续费操作完成
              try {
                await page.waitForResponse(
                  response => response.url().includes('/renew') && response.status() === 200,
                  { timeout: 10000 }
                );
              } catch (error) {
                console.log('等待续费响应超时:', error.message);
              }
              
              console.log('续费操作已提交');
              
              // 检查续费是否成功
              const renewalSuccess = await page.evaluate(() => {
                return document.body.textContent.includes('成功') || 
                       document.body.textContent.includes('success');
              });
              
              if (renewalSuccess) {
                console.log('续费成功！');
                await sendTelegramMessage(`✅ 浏览器自动化: 服务器 ${FC_MACHINE_ID} 续费成功！原剩余: ${daysLeft} 天。`);
              } else {
                console.log('可能续费失败或状态不明确');
                await sendTelegramMessage(`⚠️ 浏览器自动化: 服务器 ${FC_MACHINE_ID} 续费操作已提交，但结果不确定。请手动检查。原剩余: ${daysLeft} 天。`);
              }
            } else {
              console.log('未找到确认按钮');
              await sendTelegramMessage(`❓ 浏览器自动化: 服务器 ${FC_MACHINE_ID} 找不到续费确认按钮。请手动续费。剩余: ${daysLeft} 天。`);
            }
          } else {
            console.log('未找到续费按钮');
            await sendTelegramMessage(`❓ 浏览器自动化: 服务器 ${FC_MACHINE_ID} 找不到续费按钮。请手动续费。剩余: ${daysLeft} 天。`);
          }
        } else {
          console.log(`剩余天数为 ${daysLeft} 天，无需续费`);
          await sendTelegramMessage(`ℹ️ 浏览器自动化: 服务器 ${FC_MACHINE_ID} 剩余 ${daysLeft} 天，无需续费。`);
        }
      } else {
        console.log(`未能找到服务器 ${FC_MACHINE_ID} 的剩余天数信息`);
        await sendTelegramMessage(`⚠️ 浏览器自动化: 未能找到服务器 ${FC_MACHINE_ID} 的信息，无法续费。`);
      }
    } else {
      console.log('登录失败');
      
      // 截图保存登录失败页面
      await page.screenshot({ path: 'login_failed.png' });
      
      await sendTelegramMessage(`🔴 浏览器自动化: 登录Freecloud失败，无法续费。`);
    }
  } catch (error) {
    console.error('浏览器自动化过程中发生错误:', error);
    await sendTelegramMessage(`❌ 浏览器自动化: 过程中发生错误: ${error.message}`);
  } finally {
    await browser.close();
    console.log('浏览器已关闭');
  }
})(); 