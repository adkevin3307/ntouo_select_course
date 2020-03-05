import yaml
import time
import getpass
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class LoginException(Exception):
    pass

class CourseExistException(Exception):
    pass

def login(driver, user):
    driver.get('https://ais.ntou.edu.tw/Default.aspx')
    try:
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, 'M_PORTAL_LOGIN_ACNT')))
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, 'M_PW')))
    except TimeoutError:
        raise TimeoutError
    driver.find_element_by_name('M_PORTAL_LOGIN_ACNT').send_keys(user['account'])
    driver.find_element_by_name('M_PW').send_keys(user['password'])
    driver.find_element_by_id('LGOIN_BTN').click()
    if EC.alert_is_present()(driver):
        raise LoginException

def check_user(account, password):
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--headless')
    with webdriver.Chrome(options = options) as driver:
        try:
            login(driver, {'account': account, 'password': password})

            driver.switch_to.frame(driver.find_element_by_name('menuFrame'))
            driver.implicitly_wait(30)
            
            driver.find_element_by_xpath("//a[@title='登出']").click()
        except TimeoutError:
            raise TimeoutError
        except LoginException:
            raise LoginException

def select_course(driver, course, thread_name):
    driver.switch_to.frame(driver.find_element_by_name('menuFrame'))
    driver.implicitly_wait(30)

    driver.find_element_by_xpath("//a[@title='教務系統']").click()
    driver.find_element_by_xpath("//a[@title='選課系統']").click()
    driver.find_element_by_xpath("//a[@title='線上即時加退選']").click()

    time.sleep(3)

    driver.switch_to.default_content()
    driver.implicitly_wait(30)

    driver.switch_to.frame(driver.find_element_by_name('mainFrame'))
    driver.implicitly_wait(30)

    driver.find_element_by_name('Q_COSID').send_keys(course['id'])
    driver.find_element_by_name('QUERY_COSID_BTN').click()
    time.sleep(1)

    count = 1
    selected = []
    total_rows = int(driver.find_element_by_id('PC_TotalRow').text)

    if total_rows == 0:
        raise CourseExistException

    while (count == 1) or ((course['id'], course['class']) not in selected):
        if total_rows == 1:
            driver.find_element_by_id('DataGrid1_ctl02_edit').click()
        else:
            if int(driver.find_element_by_id('PC_PageSize').text) != 1000:
                driver.execute_script('$("#PC_PageSize").attr("value", 1000)')
                driver.find_element_by_id('PC_ShowRows').send_keys(Keys.ENTER)
                time.sleep(1)

            classes = list(map(lambda x: x.text.split()[3], driver.find_elements_by_css_selector('#DataGrid1 tbody tr')[1: ]))
            driver.find_element_by_id('DataGrid1_ctl{:02}_edit'.format(2 + classes.index(course['class']))).click()
        time.sleep(0.5)

        while True:
            try:
                alert = EC.alert_is_present()(driver)
                alert.accept()
            except:
                break
            time.sleep(1)

        selected = list(map(lambda x: tuple(x.text.split()[1: 3]), driver.find_elements_by_css_selector('#DataGrid3 tbody tr')[1: ]))
        print(f'{thread_name} ({course["id"]}): {count} times')
        count += 1

    return True

def parallel(account, password, course):
    thread_name = threading.current_thread().getName()
    print(f'==================== {thread_name} Start ====================')
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--headless')
    with webdriver.Chrome(options = options) as driver:
        try:
            login(driver, {'account': account, 'password': password})
            if select_course(driver, {'id': course['course_id'], 'class': course['class_id']}, thread_name):
                print(f'{thread_name} Success')
        except CourseExistException:
            print(f'{thread_name} ({course["course_id"]}): No Such Course')
    print(f'==================== {thread_name} Done ====================')

if __name__ == '__main__':
    with open('config.yaml', 'r') as f:
        config = yaml.load(f, Loader = yaml.FullLoader)

    try:
        account = config['account']
        password = config['password']

        check_user(account, password)

        threads = []
        course_amount = len(config['courses'])

        for i in range(course_amount):
            threads.append(threading.Thread(target = parallel, args = (account, password, config['courses'][i]), name = f'Thread {i + 1}'))
            threads[i].start()
        
        for i in range(course_amount):
            threads[i].join()
    except TimeoutError:
        print('Try Again Later')
    except LoginException:
        print('Account or Password Error')