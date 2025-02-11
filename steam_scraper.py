import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import os

# Fetch Steam sale page
res = requests.get("https://store.steampowered.com/search/?specials=1&page=2")
soup = BeautifulSoup(res.text)

# Filters for the class holding the game list
rawListData = soup.findAll("a", class_="search_result_row ds_collapse_flag")

# Creates function fetching the Steam sale list
def scrape_steam_sale_data(steampage):
    '''Fetches provided link, locates and returns raw game list data'''
    res = requests.get(steampage)
    soup = BeautifulSoup(res.text)
    rawListData = soup.findAll("a", class_="search_result_row ds_collapse_flag")
    return rawListData


# Creates function that clarifies review data
def get_steam_rating(reviewInput):
    '''Fetches and evaluates rating from 1-9 for a submitted store.steampowered.com "search_review_summary" class'''
    
    # Retrieves review info from HTML attribute
    review = reviewInput.attrs.get("data-tooltip-html")
    # Removes the break tag to access the text
    rating = review.split("<br>")[0]
    scale = {
        "Overwhelmingly Negative": 1,
        "Very Negative": 2,
        "Negative": 3,
        "Mostly Negative": 4,
        "Mixed": 5,
        "Mostly Positive": 6,
        "Positive": 7,
        "Very Positive": 8,
        "Overwhelmingly Positive": 9
    }

    result = scale.get(rating)
    return result

def get_steam_reviews(reviewInput):
    '''Fetches the number of reviews for a submitted store.steampowered.com "search_review_summary" class'''
    review = reviewInput.attrs.get("data-tooltip-html")
    
    # Fetches text between 'the' and 'user' to only retrieve the number of reviews
    sub1 = "the"
    sub2 = " user"
    idx1 = review.index(sub1)
    idx2 = review.index(sub2)
    res = ''
    for idx in range(idx1 + len(sub1) + 1, idx2):
        res = res + review[idx]
    return res


# Creates function parsing the sale list
def munge_steam_sale_data(rawListData):
    '''Processes game data from an HTML-element list, returning a list of game details.'''
    
    # Creates empty list where all game data is stored
    gameList = []
    # Loops through each row in the provided list
    for row in rawListData:
        # Specifies elements
        titleEl = row.find("span", class_="title")
        originalPriceEl = row.find("div", class_="discount_original_price")
        discountPercentEl = row.find("div", class_="discount_pct")
        finalPriceEl = row.find("div", class_="discount_final_price")
        releaseDateEl = row.find("div", class_="col search_released responsive_secondrow")
        platformWinEl = row.find("span", class_="platform_img win")
        platformMacEl = row.find("span", class_="platform_img mac")
        platformLinuxEl = row.find("span", class_="platform_img linux")
        reviewSummaryEl = row.find("span", class_="search_review_summary")

        # Uses specified elements to get text attributes or set them to None
        gameTitle = titleEl.text if titleEl else None
        originalPrice = originalPriceEl.text if originalPriceEl else None
        discountPercent = discountPercentEl.text if discountPercentEl else None
        finalPrice = finalPriceEl.text if finalPriceEl else None

        # Checks if the element exists and removes unnecessary whitespace
        if releaseDateEl and releaseDateEl.text.strip():
            releaseDate = releaseDateEl.text[3:]  # Removes '\n '
        else:
            releaseDate = None

        platformWin = 1 if platformWinEl else 0
        platformMac = 1 if platformMacEl else 0
        platformLinux = 1 if platformLinuxEl else 0
        
        if reviewSummaryEl:
            gameRating = get_steam_rating(reviewSummaryEl)
            gameReviews = get_steam_reviews(reviewSummaryEl)
        else:
            gameRating = None
            gameReviews = None
        
        finTime = datetime.now().astimezone(pytz.timezone("Europe/Helsinki"))
        time = finTime.strftime("%Y-%d-%m %H:%M:%S")
    
        gameList.append([gameTitle, gameRating, gameReviews, discountPercent,
                         finalPrice, originalPrice, releaseDate, platformWin,
                         platformMac, platformLinux, time])
    return gameList


# Creates function fetching results from a set number of pages
def get_steam_sale_pages(numberOfPages):
    '''Takes in how many pages to retrieve and process, returning a compiled DataFrame.'''
    result = []
    for i in range(1, numberOfPages+1):
        link = f"https://store.steampowered.com/search/?specials=1&page={i}"
        # Runs everything in a function
        pageData = scrape_steam_sale_data(link)
        gameList = munge_steam_sale_data(pageData)
        result.extend(gameList)

    columns = ["Game title", "Rating / 9", "#Reviews", "Discount%", "Price",
               "RegularPrice", "ReleaseYear", "Win", "Linux", "OSX", "Time"]
    df = pd.DataFrame(result, columns=columns)

    return df

# Creates function creating and updating a csv file
def save_df_csv(df, fileName="SteamSaleData.csv"):
    '''Creates and saves the provided DataFrame. If a file with the same name already exists, new and old files are combined.'''
    if os.path.exists(fileName):
        # If file exists, it is read
        existingFile = pd.read_csv(fileName)
        # Combines old and new dataframes, drops duplicates while ignoring time column.
        df = pd.concat([existingFile, df]).drop_duplicates(subset=df.columns.difference(["Time"])).reset_index(drop=True)
        
    df.to_csv(fileName, index=False)

# Runs script
saleDf = get_steam_sale_pages(5)
print(saleDf.head())

# Saves file
save_df_csv(saleDf)
