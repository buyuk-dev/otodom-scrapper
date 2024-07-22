const express = require('express');
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');

puppeteer.use(StealthPlugin());

const app = express();
const port = 3000;

let browser; // Store the browser instance

(async () => {
    browser = await puppeteer.launch({
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });
    console.log('Browser initialized');
})();

app.use(express.static('public'));

app.get('/data', (req, res) => {
    const adsDir = './ads';
    const gptDir = './gpt';
    
    const adsFiles = fs.readdirSync(adsDir).filter(file => file.endsWith('.json'));
    
    const data = adsFiles.map(file => {
        const adPath = path.join(adsDir, file);
        const gptPath = path.join(gptDir, `${file}.ai`);
        
        const adData = JSON.parse(fs.readFileSync(adPath, 'utf-8'));
        
        let gptData;
        if (fs.existsSync(gptPath)) {
            gptData = JSON.parse(fs.readFileSync(gptPath, 'utf-8'));
        } else {
            // Create a fallback gptData if the .ai file doesn't exist
            gptData = {
                Title: "Title not available",
                Location: "Location not available",
                Size: "Size not available",
                Price: { Rent: "N/A", Administrative: "N/A", Media: { included: "N/A", extra: "N/A" }, Parking: "N/A" },
                URL: "#",
                Pros: [],
                Cons: [],
                Comments: "Details not available"
            };
        }
        
        return { ad: adData, gpt: gptData };
    });

    res.json(data);
});

app.get('/fetch-html', async (req, res) => {
    const url = req.query.url;
    try {
        console.log(`Fetching URL: ${url}`);
        const page = await browser.newPage();

        // Set User-Agent and other headers to mimic a real browser
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3');
        await page.setExtraHTTPHeaders({
            'Accept-Language': 'en-US,en;q=0.9',
        });

        // Disable loading of images, stylesheets, and other non-essential resources
        await page.setRequestInterception(true);
        page.on('request', (request) => {
            if (['image', 'stylesheet', 'font'].includes(request.resourceType())) {
                request.abort();
            } else {
                request.continue();
            }
        });

        await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 2000 });

        // Retry logic for better handling dynamic content loading
        let consentButtonFound = false;
        for (let retries = 0; retries < 3; retries++) {
            try {
                //await page.waitForSelector('#onetrust-accept-btn-handler', { timeout: 20000 });
                await page.click('#onetrust-accept-btn-handler');
                consentButtonFound = true;
                break;
            } catch (e) {
                console.log(`Consent button not found, attempt ${retries + 1}`);
            }
        }

        if (!consentButtonFound) {
            console.log('Consent button not found, logging page content for debugging...');
            const pageContent = await page.content();
            console.log(pageContent);
        }

        // Ensure the page is fully loaded before extracting content
        //await page.waitForTimeout(5000); // Wait for additional content load
        const content = await page.content();
        await page.close();
        res.send(content);
    } catch (error) {
        console.error(`Error fetching URL: ${url}`, error);
        res.status(500).send('Error fetching the URL');
    }
});

app.listen(port, () => {
    console.log(`Server is running at http://localhost:${port}`);
});