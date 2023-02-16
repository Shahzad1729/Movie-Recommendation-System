import requests

def fetch_release_date_webShow(web_show_id):
    url = f"https://omdbapi.com/?i={web_show_id}&apikey=9c1e59c"
    data = requests.get(url)
    data = data.json()
    try:
        release_date=data['Year']
        return release_date.replace("-","")
    except Exception as e:
        release_date=""
        return release_date

def fetch_poster_webShow(web_show_id):
    url=f"https://omdbapi.com/?i={web_show_id}&apikey=9c1e59c"
    data=requests.get(url)
    data=data.json()
    try:  
        poster_path = data['Poster']
        full_path = poster_path
    except TypeError:
        full_path = "https://i.ibb.co/ThSbsxD/no-image.png"
    except KeyError:
        full_path = "https://i.ibb.co/ThSbsxD/no-image.png"
    return full_path

def fetch_release_date(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=eed0167c409a32158f097afcde988d54".format(
        movie_id)
    data = requests.get(url)
    data = data.json()
    try:
        release_date=data['release_date']
        release_date=release_date.split("-")
        return release_date[0]
    except Exception as e:
        release_date=""
        return release_date

def fetch_poster(movie_id):
    url="https://api.themoviedb.org/3/movie/{}?api_key=eed0167c409a32158f097afcde988d54".format(movie_id)
    data=requests.get(url)
    data=data.json()
    try:  
        poster_path = data['poster_path']
        full_path = "https://image.tmdb.org/t/p/w500/"+poster_path
    except TypeError:
        full_path = "https://i.ibb.co/ThSbsxD/no-image.png"
    except KeyError:
        full_path = "https://i.ibb.co/ThSbsxD/no-image.png"
    return full_path