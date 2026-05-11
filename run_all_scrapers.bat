@echo off
setlocal enabledelayedexpansion

echo ============================================
echo Running All Company Job Scrapers
echo ============================================

set SCRAPERS=Accenture.py Adobe.py AECOM.py Airbus.py AlvarezMarshal.py Amazon.py AMD.py AEXP.py Apple.py Atlassian.py BainCompany.py BankofAmerica.py BCG.py Capgemini.py Cisco.py Cognizant.py Cummins.py Dell.py Deloitte.py DXC.py Ericcson.py EY.py Fidelity.py Flipkart.py Google.py Goldmansach.py HclTech.py Hexaware.py Ibm.py Intel.py Infosys.py Jpmorgan.py LT.py Mahindra.py Mckinsey.py Microsoft.py Mphasis.py MorganStanley.py Nestle.py Nvidia.py Oracle.py Paypal.py Pepsico.py Pfizer.py Phillips.py PWC.py Qualcomm.py Razorpay.py SAPlabs.py Samsung.py Siemens.py Stripe.py Synopsis.py TechM.py TCS.py Uber.py Visa.py Walmart.py Zoho.py

for %%S in (%SCRAPERS%) do (
    echo.
    echo ============================================
    echo Running %%S
    echo ============================================

    python %%S

    if errorlevel 1 (
        echo ❌ %%S failed
    ) else (
        echo ✅ %%S completed
    )

    timeout /t 5 /nobreak >nul
)

echo.
echo ============================================
echo All Python Scrapers Finished!
echo ============================================

echo.
echo Now running Node portal scraper...
node scraper.js

if errorlevel 1 (
    echo ❌ scraper.js failed
) else (
    echo ✅ scraper.js completed
)

echo.
echo ============================================
echo All Scrapers Finished!
echo ============================================

pause
