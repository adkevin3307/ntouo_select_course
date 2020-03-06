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

    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, 'M_PORTAL_LOGIN_ACNT')))
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, 'M_PW')))

    driver.find_element_by_name('M_PORTAL_LOGIN_ACNT').send_keys(user['account'])
    driver.find_element_by_name('M_PW').send_keys(user['password'])
    driver.find_element_by_id('LGOIN_BTN').click()

    if EC.alert_is_present()(driver):
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
            if int(driver.find_element_by_id('PC_PageSize').text) != 100:
                driver.execute_script('$("#PC_PageSize").attr("value", 100)')
                driver.find_element_by_id('PC_ShowRows').send_keys(Keys.ENTER)

            WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#DataGrid1 tbody tr')))
            classes = list(map(lambda x: x.text.split()[3], driver.find_elements_by_css_selector('#DataGrid1 tbody tr')[1: ]))
            driver.find_element_by_id('DataGrid1_ctl{:02}_edit'.format(2 + classes.index(course['class']))).click()

        while True:
            try:
                WebDriverWait(driver, 3).until(EC.alert_is_present())
            except:
                break
            driver.switch_to.alert.accept()

        WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, '#DataGrid3 tbody tr')))
        selected = list(map(lambda x: tuple(x.text.split()[1: 3]), driver.find_elements_by_css_selector('#DataGrid3 tbody tr')[1: ]))
        print(f'{thread_name} ({course["id"]}): {count} times')
        count += 1

    return True

def parallel(account, password, course):
    thread_name = threading.current_thread().getName()
    print(f'==================== {thread_name} Start ====================')
    options = webdriver.ChromeOptions()
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # options.add_argument('--headless')
    with webdriver.Chrome(options = options) as driver:
        try:
            login(driver, {'account': account, 'password': password})
            if select_course(driver, {'id': course['course_id'], 'class': course['class_id']}, thread_name):
                print(f'{thread_name} Success')
        except TimeoutError:
            print(f'{thread_name} ({course["course_id"]}): Timeout')
        except LoginException:
            print(f'{thread_name} ({course["course_id"]}): Account or Password Error')
        except CourseExistException:
            print(f'{thread_name} ({course["course_id"]}): No Such Course')
    print(f'==================== {thread_name} Done ====================')

if __name__ == '__main__':
    with open('config.yaml', 'r') as f:
        config = yaml.load(f, Loader = yaml.FullLoader)

    account = config['account']
    password = config['password']

    threads = []
    course_amount = len(config['courses'])

    for i in range(course_amount):
        threads.append(threading.Thread(target = parallel, args = (account, password, config['courses'][i]), name = f'Thread {i + 1}'))
        threads[i].start()
    
    for i in range(course_amount):
        threads[i].join()