from glob import glob
import os
from pickle import FALSE
import platform
import json
import requests
import time
import re
from datetime import timedelta
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

global driver
global assetName
global assetPeriod

# Constants
# Regex
REGEX_ASSET = "\w{3,} (15|30|60|90|120)"
# Elements
SEARCH_BAR_ID = "savings-search-coin"
ASSET_TITLE_CLASS = "css-1onbf4e"
STAKE_BTN_ID = "pos-stake"
MAX_BTN_CLASS = "css-joha13"
AUTO_STAKE_SWITCH_CLASS = "css-1bbf0ma"
ACCEPT_TERMS_XPATH = "//div[4]/div/div[4]/label/div"
MODAL_TITLE_CLASS = "modal-title"
ACCEPT_TERMS_AUTOSTAKE_CLASS = "css-pf8gn9"
ACCEPT_AUTOSTAKE_CLASS = "css-d1jly6"
CONFIRM_BTN_ID = "pos-confirm"
LOCK_AMO_CLASS = "css-16fg16t"
AVAILABLE_AMO_CLASS = "css-87q6r1"
ACCEPT_COOKIES_BTN_ID = "onetrust-accept-btn-handler"
LABEL_HELPER_CLASS = "bn-input-helper-text"
# URLs
API_URL = "https://www.binance.com/gateway-api/v1/friendly/pos/union?pageSize=200&pageIndex=1&status=ALL"
LOGIN_URL = "https://accounts.binance.com/es/login"
POS_URL = "https://www.binance.com/es/pos"
POST_LOGIN_URL = "https://www.binance.com/es/my/dashboard"


def scrollAndClick(element):
    driver.execute_script("arguments[0].scrollIntoView();", element)
    element.click()


def waitForElement(element):
    WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable(element))


def waitAndClick(element):
    waitForElement(element)
    element.click()


def searchAsset():
    while True:
        driver.refresh()

        searchBar = driver.find_element(By.ID, SEARCH_BAR_ID)

        searchBar.send_keys(assetName)  # write asset name on search bar

        while len(driver.find_elements(By.CLASS_NAME, ASSET_TITLE_CLASS)) != 1:
            time.sleep(0.2)
            len(driver.find_elements(By.CLASS_NAME, ASSET_TITLE_CLASS))

        # select period (days)
        driver.find_element(
            By.XPATH, '//button[contains(text(), ' + str(assetPeriod) + ')]').click()

        time.sleep(0.1)

        if driver.find_elements(By.ID, STAKE_BTN_ID) == 0:
            writeToLog("Asset sold out. Retrying...")
            continue
        else:
            print("  Asset available")
            break


def compareLockAndAvailableAmount():
    lockAmount = driver.find_element(
        By.CLASS_NAME, LOCK_AMO_CLASS).get_attribute("value")
    availableAmount = driver.find_element(
        By.CLASS_NAME, AVAILABLE_AMO_CLASS).get_attribute("innerText").split()[-2].rstrip("0")

    if lockAmount != availableAmount:
        writeToLog(
            "Lock amount (" + lockAmount + ") and available amount (" + availableAmount + ") are not matching. Retrying...")
        return False

    return True


def autoStakeAcceptTerms():
    waitForElement(driver.find_element(By.CLASS_NAME, MODAL_TITLE_CLASS))
    checkboxes = driver.find_elements(
        By.CLASS_NAME, ACCEPT_TERMS_AUTOSTAKE_CLASS)
    for checkbox in checkboxes:
        checkbox.click()
    driver.find_element(By.CLASS_NAME, ACCEPT_AUTOSTAKE_CLASS).click()


def startStaking(autoStake):
    while True:
        searchAsset()
        print("  Starting subscription...")

        try:
            time.sleep(0.3)

            # open stake panel
            driver.find_element(By.ID, STAKE_BTN_ID).click()

            # select max quantity
            waitAndClick(driver.find_element(By.CLASS_NAME, MAX_BTN_CLASS))

            time.sleep(0.2)

            if len(driver.find_elements(By.CLASS_NAME, LABEL_HELPER_CLASS)) != 0:
                writeToLog(driver.find_element(By.CLASS_NAME, LABEL_HELPER_CLASS).get_attribute(
                    "innerText"))
                return

            if not compareLockAndAvailableAmount():
                continue

            if not autoStake:
                scrollAndClick(driver.find_element(
                    By.CLASS_NAME, AUTO_STAKE_SWITCH_CLASS))

            # accept terms and conditions
            driver.find_element(By.XPATH, ACCEPT_TERMS_XPATH).click()

            time.sleep(0.2)

            # driver.find_element(By.ID, CONFIRM_BTN_ID).click()  # confirm

            if autoStake:
                autoStakeAcceptTerms()

            writeToLog("  Subscription completed successfully!")

        except Exception as e:
            print(e)
            writeToLog("  Something went wrong. Retrying...")


def writeToLog(text):
    now = datetime.now()
    dateTime = now.strftime("%d/%m/%Y, %H:%M:%S")

    print("  " + text)

    f = open("abs_log.txt", "a")
    f.write(assetName + assetPeriod + "\t" + dateTime + "\t" + text + "\n")
    f.close()


def initWebDriver():
    print(" --------------------------------------------")
    print("  Starting web driver...")
    print(" --------------------------------------------")

    while True:
        try:
            driver = webdriver.Firefox()
            break
        except:
            try:
                driver = webdriver.Chrome()
                break
            except:
                try:
                    driver = webdriver.Safari()
                    break
                except:
                    input('''
  Error: web driver not found.
  Please, download the web driver
  https://www.selenium.dev/documentation/webdriver/getting_started/install_drivers/
  Press enter when you are done
  >
'''
                    )

    driver.maximize_window()

    return driver


def openLoginAndPos():
    openWebsite(LOGIN_URL)

    waitAndClick(driver.find_element(By.ID, ACCEPT_COOKIES_BTN_ID))

    while driver.current_url != POST_LOGIN_URL:
        time.sleep(0.2)

    openWebsite(POS_URL)


def openWebsite(website):
    while True:
        try:
            driver.get(website)
            break
        except:
            showNetworkError()
            continue


def showNetworkError():
    input('''
  Error: we weren't able to open the website
  Please, check your internet connectio and
  press enter to retry
  >
'''
          )


def checkAssetAvailability(checkingInterval):
    while True:
        # Request data from binance
        try:
            response = json.loads(requests.get(API_URL).text)["data"]
        except:
            # Couldn't get json data. Sleep and retry
            time.sleep(1000)
            continue

        # Unpacking results
        avaliables = unpackResponse(response)

        for item in avaliables:
            if assetName == item["asset"] and assetPeriod == item["duration"]:
                print(" Asset found:")
                print(
                    f" {item['asset']} for {item['duration']}d / {item['APY']}% APY")
                print("--------------------------------------------")
                return True

        # time loop waiting
        time.sleep(timedelta(seconds=checkingInterval).total_seconds())


def unpackResponse(response):
    avaliables = []

    for item in response:
        for asset in item["projects"]:
            if not asset["sellOut"]:
                # Asset available, adding a dictionary with asset name, duration and APY to the result list
                avaliables.append({
                    "asset": asset["asset"],
                    "duration": asset["duration"],
                    "APY": str(round(float(asset["config"]["annualInterestRate"]) * 100, 2))
                })

    return avaliables


def showAssetInfo(checkingInterval, autoStake, shutdown):
    print("""
 --------------------------------------------
       Automatic Binance Locked staking
 --------------------------------------------
  Searching for...
  Asset: %s
  Period: %s days
 --------------------------------------------
  Checking every %s seconds
  Auto-stake: %s
  Shutdown after subscription: %s
 --------------------------------------------
""" % (assetName, assetPeriod, str(checkingInterval), "yes" if autoStake else "no", "yes" if shutdown else "no")
    )


def end(shutdown):
    print("Bye!")
    osName = platform.system()

    if shutdown:
        if osName == 'Linux':
            os.system('systemctl poweroff')
        elif osName == 'Darwin':
            os.system('shutdown -h now')
        elif osName == 'Windows':
            os.system('shutdown -s -t 0')

    exit()


def main():
    global driver
    global assetName
    global assetPeriod

    try:
        print(" --------------------------------------------")
        print("       Automatic Binance Locked Staking")
        print(" --------------------------------------------")
        print("  Please, type the target asset")
        print("  Examples: 'LUNA 90', 'AXS 60'...")
        print(" --------------------------------------------")

        while True:
            targetAsset = input(" >")

            if re.search(REGEX_ASSET, targetAsset):
                assetName, assetPeriod = targetAsset.split(" ")
                break
            else:
                print("  Wrong asset pattern. Try again.")

        while True:
            print(" --------------------------------------------")
            print("  Enter checking interval in seconds")
            print(" --------------------------------------------")
            checkingInterval = input("  >")

            if checkingInterval.isnumeric():
                checkingInterval = int(checkingInterval)
                if checkingInterval >= 0:
                    break
            else:
                print("  Wrong checking interval")

        print(" --------------------------------------------")
        print("  Do you want to enable auto-stake? (y/n)")
        print(" --------------------------------------------")
        autoStake = True if input("  >").lower() == 'y' else False

        print(" --------------------------------------------")
        print("  Do you want to shutdown your computer")
        print("  after subscripion? (y/n)")
        print(" --------------------------------------------")
        shutdown = True if input("  >").lower() == 'y' else False

        driver = initWebDriver()

        showAssetInfo(checkingInterval, autoStake, shutdown)

        openLoginAndPos()

        if checkAssetAvailability(checkingInterval):
            startStaking(autoStake)

        end(shutdown)

    except:
        exit()


if __name__ == "__main__":
    main()
