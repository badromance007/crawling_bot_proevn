import xlrd 
import json
from glob import glob

import bs4
import pandas
from pandas import *
import requests
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
# import time
import os # write files
from tqdm import tqdm # for images downloading progress bar
# from unidecode import unidecode


names = []
desc_smalls = []
new_prices = []
amounts = []
paths = []
image_urls = []

def get_page_content(url):
  page = requests.get(url,headers={"Accept-Language":"en-US"})
  return bs4.BeautifulSoup(page.text,"html.parser")

def get_page_html(url):
  options = webdriver.ChromeOptions()
  options.add_argument('--ignore-certificate-errors')
  options.add_argument('--incognito')
  options.add_argument('--headless')
  options.add_argument('--no-sandbox') # Bypass OS security model
  driver = webdriver.Chrome("chromedriver.exe", options=options)
  
  driver.get(url)
  delay = 30 # seconds
  data_image = ''
  try:
    small_images = driver.find_elements_by_css_selector("#gallery_01 img")
    for image in small_images:
      print(f"Before Waiting /images/loader.gif => {image.get_attribute('src')}")
      WebDriverWait(driver, delay).until(lambda x: data_image not in image.get_attribute('src'))
      print(f"After Waiting /images/loader.gif => {image.get_attribute('src')}")
    print("Page is ready!")
  except TimeoutException:
    print("Loading took too much time!")
  page = driver.page_source
  # driver.quit()
  
  return bs4.BeautifulSoup(page,"lxml")

def download(image_url, pathname, name):
  # Downloads an image given an URL and puts it in the folder `images`
  # if images doesn't exist, make that images dir
  if image_url != '':
    if not os.path.isdir(pathname):
      print('Create images folder!')  
      os.makedirs(pathname)
    print('===================================================')
    print(image_url)
    print('===================================================')
    image_url = f"https://{image_url.split('//')[-1]}"
    print('===========>')
    print(f"{image_url}")
    response = requests.get(image_url, stream=True) # download response body
    file_size = int(response.headers.get("Content-Length", 0)) # get filesize
    filename = os.path.join(pathname, f"{name}.{image_url.split('.')[-1].split('?')[0]}") # # get the file name
    # progress bar, changing the unit to bytes instead of iteration (default by tqdm)
    progress = tqdm(response.iter_content(1024), f"Downloading {filename}", total=file_size, unit="B", unit_scale=True, unit_divisor=1024)
    with open(filename, "wb") as f:
        for data in progress:
            # write data read to the file
            f.write(data)
            # update the progress bar manually
            progress.update(len(data))
    return True
  else:
    return False


def get_page_details(paths, product_codes, logs_foder):
  categories = []
  image_amounts = []
  details = []
  crawled_urls = []
  crawled_index_at = 0

  # check if logs.xlsx file exists and determine crawling
  if os.path.exists(f"{logs_foder}/logs.xlsx"):
    print(f"BACKUP FILE EXISTS- {logs_foder}/logs.xlsx is being read")
    wb = xlrd.open_workbook(f"{logs_foder}/logs.xlsx")
    sheet = wb.sheet_by_index(0) 
    sheet.cell_value(0, 1)
    d_log = {
      'crawled_urls': [],
      'downloaded_image_amounts': [],
      'downloaded_categories': [],
      'downloaded_details': []
    }
    for i in range(sheet.nrows):
      if i >= 1:
        d_log['crawled_urls'].append(sheet.cell_value(i, 1))
        d_log['downloaded_image_amounts'].append(sheet.cell_value(i, 2))
        d_log['downloaded_categories'].append(sheet.cell_value(i, 3))
        d_log['downloaded_details'].append(sheet.cell_value(i, 4))

    crawled_urls = d_log['crawled_urls']
    image_amounts = d_log['downloaded_image_amounts']
    categories = d_log['downloaded_categories']
    details = d_log['downloaded_details']
    crawled_index_at = len(crawled_urls) # remember crawled position
    print(f"crawled_index_at -> {crawled_index_at}")
    print(f"paths length before remove -> {len(paths)}")
    for crawled_url in crawled_urls:
      paths.remove(crawled_url) # remove crawled paths
    print(f"paths length after remove -> {len(paths)}")
  else:
    print(f"BACKUP FILE DOES NOT EXISTS!!!")

  for index, path in enumerate(paths):
    print(f"paths length looping -> {len(paths)}")
    url = "https://www.proe.vn" + path

    # get detail
    soup = get_page_html(url)

    category = soup.findAll('a', {"itemprop": "url"})[1]
    
    image_container = soup.find('div', {"id": "gallery_01"})
    
    if image_container == None:
      print(f"image_container is NONE!!!!")
      image_tags = [soup.find('img', {"id": "zoom_01"})]
      image_urls = [image_tag.get('src') for image_tag in image_tags]
      print(f"Image urls when container NONE =====> {image_urls}")
    else:
      image_tags = image_container.findAll('div', {"class": "owl-item"})
      image_urls = [image_tag.find('img').get('src') for image_tag in image_tags]
    download_fail_count = 0
    download_status = True
    for i, image_url in enumerate(image_urls):
      image_url = image_url.replace('small', 'grande')
      if i == 0:
        download_status = download(image_url, f"images", product_codes[index + crawled_index_at]) # download first images
        if download_status == False:
          print(" ")
          print("Cannot Download First Image.... Stop program!!!!") # for examination!!!!
          print(" ")
          exit()
      else:
        if download_fail_count == 0:
          download_status = download(image_url, f"images", f"{product_codes[index + crawled_index_at]}_{i}") # download remaining images
          if download_status == False:
            download_fail_count += 1
        else:
          download_status = download(image_url, f"images", f"{product_codes[index + crawled_index_at]}_{i - download_fail_count}") # download remaining images
          if download_status == False:
            download_fail_count += 1


    detail = soup.find('div', class_='product-well')

    print(f"{index + crawled_index_at}.Crawling -> {url}")
    for image_url in image_urls:
      print(f"{index + crawled_index_at}.{image_url}")

    # details.append(url)
    image_amounts.append(len(image_urls) - download_fail_count)
    details.append(detail)
    crawled_urls.append(path)
    categories.append(category.find('span').text)
    
    # create logs for backup
    if not os.path.isdir(logs_foder):
      print('Create logs folder!')  
      os.makedirs(logs_foder)
    logs_backup = {
      'crawled_urls': crawled_urls,
      'downloaded_image_amounts': image_amounts,
      'downloaded_categories': categories,
      'downloaded_details': details
    }
    # update logs.xlsx backup file
    df_backup = pandas.DataFrame(logs_backup)
    df_backup.to_excel(f"{logs_foder}/logs.xlsx")
    print(f"BACKUP FILE - {logs_foder}/logs.xlsx is updated")

  return [image_amounts, details, categories]


def collect_data(array_data):
  global names
  global desc_smalls
  global new_prices
  global amounts
  global paths

  for item in array_data:
    for page in range(1,(item['page']+1)):
      url = f"{item['url']}&page={page}"
      soup = get_page_content(url)

      container = soup.find('section', {"class": "products-view"})
      if container is None: # Case: Page does not exist!!!
        print(f"Container is None ====> Page {url} - DOES NOT EXIST!!!")
        exit() # stop for determination
        continue # skip the page
      
      products = container.findAll('h3', class_='product-name')
      descriptions = products
      price_tags = container.findAll('span', class_='price')
      prices = [0 if price.text.strip() == 'Liên hệ' else int(price.text.strip().replace('.', '').replace('₫', '').replace(' -', '')) for price in price_tags]
      amount_tags = products
      

      names += [product.find('a').text for product in products]
      desc_smalls += [description.find('a').text for description in descriptions]
      new_prices += [int(round((price + price * 15 / 100)/500.0) * 500.0) for price in prices]
      amounts += [ 1 for amount in amount_tags]

      paths += [product.find('a')['href'] for product in products]
      print(url)

print("Start crawling...")
sub_child_list_data = []
try:
  f = open(f"products.json", encoding="utf8")
  sub_child_list_data = json.load(f)
  f.close()
except:
  print(f"products.json does not exist!")

print(sub_child_list_data)
if len(sub_child_list_data) > 0:
  array_data = sub_child_list_data
  
  # Empty old values for global variables first
  names = []
  desc_smalls = []
  new_prices = []
  amounts = []
  paths = []
  image_urls = []
  # call function: start crawling....
  collect_data(array_data)

  print(f"names length = {len(names)}")
  print(f"desc_smalls length = {len(desc_smalls)}")
  print(f"new_prices length = {len(new_prices)}")
  print(f"amounts length = {len(amounts)}")
  print(f"image_urls length = {len(image_urls)}")
  print(f"paths length = {len(paths)}")

  product_codes = [array_data[0]['codeprefix'] + str(index).zfill(3) for index, name in enumerate(names)]
  print(names)
  print(paths)
  page_detail = get_page_details(paths, product_codes, "logs")
  df1 = pandas.DataFrame({'Danh mục cấp 1':['' for category in page_detail[2]],
                          'Danh mục cấp 2':['' for category in page_detail[2]],
                          'Danh mục cấp 3':page_detail[2],
                          'Mã SP':product_codes,
                          'Tên':names,
                          'Mô tả':desc_smalls,
                          'Giá bán':new_prices,
                          'Số lượng tồn':amounts,
                          'Số lượng ảnh':page_detail[0],
                          'Nội dung':page_detail[1]})

  print(df1)
  if not os.path.isdir(f"excels"):
    print('Create excels folder!')  
    os.makedirs(f"excels")
  df1.to_excel(f"excels/{array_data[0]['filename']}.xlsx")

  # create json file
  result = df1.to_json (orient='records')
  print(result)
  parser = json.loads(result)
  print(parser)
  with open(f"excels/{array_data[0]['filename']}.json", 'w', encoding='utf-8') as f:
    json.dump(parser, f, ensure_ascii=False, indent=4)
