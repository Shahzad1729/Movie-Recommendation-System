from utilityFunctions import *
from SqlQuery import *
from flask import Flask, redirect, render_template, request, jsonify, url_for, session
import operator
from annoy import AnnoyIndex
from flask_mail import Mail, Message
from random import randint
from flask_cors import CORS, cross_origin
import pickle
from fetchingData import *

# Hollywood Movies : 4808
# Indian Movies : 3146


app = Flask(__name__)
app.secret_key = "secret key"
CORS(app, support_credentials=True)


# Flask mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = "recmovie254@gmail.com"
app.config['MAIL_PASSWORD'] = "vpxtvcgntuunpssc"
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)


# fetch movies data
conn = db_connection("movies")
cursor = conn.cursor()
cursor.execute(FETCH_ALL_MOVIES)
movies_result = cursor.fetchall()
conn.close()



#----------------------------------------------- Hollywood Movie Recommendation-----------------------------------------



# Home page
@app.route('/')
def index():
    return render_template("index.html")


# Signup page
signup_email = ""
signup_password = ""
signup_mobile = ""
@app.route('/signup', methods=['GET','POST'])
def signup():
    global signup_email
    global signup_password
    global signup_mobile
    response = render_template("signup.html")

    if request.method == 'POST':
        conn = db_connection("users")
        cursor = conn.cursor()

        signup_email = request.form["email"]
        signup_mobile = request.form["mobile"]
        signup_password = request.form["password"]

        sql_query = "Select email from users where email= '"+signup_email+"'"
        cursor.execute(sql_query)
        results = cursor.fetchall()
        conn.close()

        if len(results) != 0:
            response = "This email is already registered. <br> Please sign-in."
        else:
            session["user"] = signup_email
            session["choices"] = 0
            response = "choices"
    return response


# Signin page
signin_email = ""
@app.route('/signin', methods=['GET','POST'])
def signin():
    global signin_email
    response = render_template("signin.html")

    if request.method == 'POST':
        conn = db_connection("users")
        cursor = conn.cursor()

        signin_email = request.form["email"]
        password = request.form["password"]

        sql_query = "Select email, password from users where email= '"+signin_email+"'"
        cursor.execute(sql_query)
        results = cursor.fetchall()
        conn.close()

        if len(results) == 0:
            response = "This email is not registered. <br> Please sign-up first."
        elif password != results[0][1]:
                response = "Incorrect Password."
        elif password == results[0][1]:
            session["user"] = signin_email
            session["choices"] = 1
            response = "recommendations"

    return response


# Choices page
@app.route('/choices', methods=['GET','POST'])
def choices():
    global signup_email
    global movies_result
    if "user" in session:
        if "choices" in session and session["choices"] == 1:
            return redirect(url_for("recommendations"))
        else:
            genre_names = []
            cast_dict = {}
            for row in movies_result:
                mov_gen = list(row[5].split("$"))
                for gen in mov_gen:
                    if gen not in genre_names and gen != '':
                        genre_names.append(gen)

                mov_cast = list(row[7].split("$"))
                for cast in mov_cast:
                    if cast in cast_dict and cast != '':
                        cast_dict[cast] = (cast_dict[cast] + 1)
                    else:
                        cast_dict[cast] = 0

            cast_dict = dict(sorted(cast_dict.items(), key=operator.itemgetter(1), reverse=True))
            cast_names = []
            counter = 0
            for key in cast_dict:
                if counter < 25:
                    cast_names.append(key)
                    counter += 1
                else:
                    break

            return render_template("choices.html", genre_names=genre_names, cast_names=cast_names)
    else:
        print("Session not found")
        return redirect(url_for("signup"))


movie_names = []
for row in movies_result:
    movie_names.append(row[2])

@app.route('/getByGenre', methods=['GET','POST'])
def getByGenre():
    genre = request.form["genre"]
    genre_movies, genre_posters = byGenre(genre, movies_result)
    response = jsonify(
        {"genre_movies": genre_movies}, {"genre_posters": genre_posters}
    )
    return response


@app.route('/getByYear', methods=['GET','POST'])
def getByYear():
    year = request.form["year"]
    year_movies, year_posters = byYear(year, movies_result)
    response = jsonify(
        {"year_movies": year_movies}, {"year_posters": year_posters}
    )
    return response


# Recommendations page
@app.route('/recommendations', methods=['GET', 'POST'])
def recommendations():
    global signin_email
    global signup_email

    if "user" in session:
        conn = db_connection("users")
        cursor = conn.cursor()
        selected_genres = []
        selected_cast = []

        sql_query = " Select selected_genres, selected_cast from users where email= '" + session["user"] + "'"
        cursor.execute(sql_query)
        results = cursor.fetchall()

        # sign-in
        if len(results) != 0:
            selected_genres = list(results[0][0].split("$"))
            selected_cast = list(results[0][1].split("$"))

        # sign-up
        else:
            genreList = request.form.getlist('genre-checkbox')
            castList = request.form.getlist('cast-checkbox')
            for i in genreList:
                selected_genres.append(i.replace("-", " "))
            for i in castList:
                selected_cast.append(i.replace("-", " "))

            # insert into database on signup
            sg = ("$".join(selected_genres))
            sc = ("$".join(selected_cast))
            global signup_password
            global signup_mobile
            cursor.execute(INSERT_USER, (signup_email, signup_password, signup_mobile, sg, sc))
            conn.commit()
            print(cursor.lastrowid)
            conn.close()
            # session["choices"] = 1

        conn.close()
        choice_movies = byChoice(selected_genres, selected_cast)
        choice_idx = []
        choice_posters = []
        for mov in choice_movies:
            for row in movies_result:
                if row[2] == mov:
                    movie_idx = row[0]
                    movie_id = row[1]
                    break;
            choice_idx.append(movie_idx)
            choice_posters.append(fetchBackdrop(movie_id))
        genre_movies, genre_posters = byGenre("Action", movies_result)
        year_movies, year_posters = byYear("2016", movies_result)

        return render_template("recommendations.html", movie_names=movie_names, genre_movies=genre_movies, year_movies=year_movies, genre_posters=genre_posters, year_posters=year_posters, choice_idx=choice_idx, movies_result=movies_result, choice_posters=choice_posters)
    else:
        print("Session not found")
        return redirect(url_for("signin"))


# Movie page
@app.route('/movie/<movie_name>')
def movie(movie_name):
    if "user" in session:
            def recommend(movie):
                for row in movies_result:
                    if row[2] == movie:
                        movie_index = row[0]
                        break;
                u = AnnoyIndex(5000, 'angular')
                u.load('./model/hollywood/vectors.ann')
                movies_list = (u.get_nns_by_item(movie_index, 7))[1:7]  # returns index of 6 similar movies

                recommended_movies = []
                movie_posters = []
                for i in movies_list:
                    rec_movie_id = movies_result[i][1]
                    recommended_movies.append(movies_result[i][2])
                    movie_posters.append(fetchPoster(rec_movie_id, movies_result))
                return recommended_movies, movie_posters

            selected_movie = movie_name
            for row in movies_result:
                if row[2] == selected_movie:
                    movie_idx = row[0]
                    movie_id = row[1]
                    break
            recommendations, posters = recommend(selected_movie)
            trailer_key = fetchTrailer(movie_id, movies_result)
            movie_poster = fetchPoster(movie_id, movies_result)

            mov_genre = []
            mov_cast = []
            for row in movies_result:
                mg = list(row[5].split("$"))
                mov_genre.append(mg)
                mc = list(row[7].split("$"))
                mov_cast.append(mc)

            return render_template("movie.html", movie_names=movie_names, movies_result=movies_result, movie_idx=movie_idx, recommendations=recommendations, posters=posters, trailer_key=trailer_key, movie_poster=movie_poster, mov_genre=mov_genre, mov_cast=mov_cast)
    else:
        print("Session not found")
        return redirect(url_for("signin"))

# Watch page
@app.route('/watch/<movie_name>')
def watch(movie_name):
    if "user" in session:
        return render_template("watch.html", movie_name=movie_name, movie_names=movie_names)
    else:
        print("Session not found")
        return redirect(url_for("signin"))


otp = ""
# Forgot page
@app.route('/forgot', methods=['POST', 'GET'])
def forgot():
    global signin_email
    global otp

    response = render_template("forgotPass.html")
    if request.method == 'POST':
        conn = db_connection("users")
        cursor = conn.cursor()

        signin_email = request.form["email"]

        sql_query = "Select email, password from users where email= '"+signin_email+"'"
        cursor.execute(sql_query)
        results = cursor.fetchall()
        conn.close()

        if len(results) == 0:
            response = "This email is not registered. <br> Please sign-up first."
        else:
            response = "forgot"

    if response == "forgot":
        range_start = 10**(6-1)
        range_end = (10**6)-1
        otp = randint(range_start, range_end)
        message = Message("Movie Mate | OTP for password reset", sender="recmovie254@gmail.com", recipients=[signin_email])
        message.body = "OTP: "+str(otp)
        mail.send(message)

    return response


# reset page
@app.route('/reset', methods=['GET','POST'])
def reset():
    global otp
    response = render_template("reset.html")
    if request.method == 'POST':
        num = request.form["otp"]
        if str(num) == str(otp):
            response = "valid"
        else:
            response = "OTP entered is incorrect"

    return response


# change password in database
@app.route('/change', methods=['GET','POST'])
def change():
    global signin_email
    if request.method == 'POST':
        newPass = request.form["newPass"]
        conn = db_connection("users")
        cursor = conn.cursor()
        sql_query = "Update users set password = '"+newPass+"' where email = '"+signin_email+"'"
        cursor.execute(sql_query)
        conn.commit()
        conn.close()
        session["user"] = signin_email
        session["choices"] = 1

    return "recommendations"

# Logout
@app.route('/logout')
def logout():
    session.pop("user", None)
    session.pop("choices", None)
    return redirect(url_for("index"))



#----------------------------------------------- Indian Movie Recommendation-----------------------------------------


def db_connect(db_name):
    conn = None
    try:
        conn = sqlite3.connect("./model/indian/"+db_name+".sqlite")
    except sqlite3.error as e:
        print(e)
    return conn

conn = db_connect("movies")
cursor = conn.cursor()
cursor.execute(FETCH_ALL_MOVIES)
indian_movies_result = cursor.fetchall()
conn.close()


def fetch_movie_details(movie_index):
    movie_id=""
    desc=""
    actors=""
    genre=""
    actors=""
    for row in indian_movies_result:
        if row[0]==movie_index:
            movie_id=row[2]
            desc=row[4]
            genre=row[3].split("$")
            actors=list(row[5].split("$"))
    return movie_id,desc,genre,actors

# Function to recommend Indian Movies

def indrecommend(movie):
    for row in indian_movies_result:
        if row[1]==movie:
            index=row[0]
    current_movie_id,current_movie_overview,current_movie_genre,current_movie_cast=fetch_movie_details(index)
    current_movie_poster=fetch_poster(current_movie_id)
    current_movie_release_date=fetch_release_date(current_movie_id)
    u = AnnoyIndex(3000, 'angular')
    u.load('./model/indian/vectors.ann')
    movies_list = (u.get_nns_by_item(index, 8))[1:8]
    recommended_movies_name=[]
    recommended_movies_poster=[]
    recommended_movies_release_dates=[]
    for i in movies_list:
        for row in indian_movies_result:
            if row[0]==i:
                movie_id=row[2]
                movie_name=row[1]
        recommended_movies_poster.append(fetch_poster(movie_id))
        recommended_movies_release_dates.append(fetch_release_date(movie_id))
        recommended_movies_name.append(movie_name)
    return recommended_movies_name,recommended_movies_poster,recommended_movies_release_dates,current_movie_overview,current_movie_release_date,current_movie_genre,current_movie_cast,current_movie_poster

# Providing Indian Movies names in list
indian_movies_names=[]
for row in indian_movies_result:
    indian_movies_names.append(row[1])

# Indian Movie
@app.route('/indian_movie/<movie_name>')
def indian_movie(movie_name):
    if "user" in session:
            try:
                movies_name=movie_name
                recommended_movies_name,recommended_movies_poster,recommended_movies_release_dates,current_movie_overview,current_movie_release_date,current_movie_genre,current_movie_cast,current_movie_poster=indrecommend(movies_name)
                return render_template("indianMovies.html",recommendations=recommended_movies_name,movie_names=indian_movies_names,poster=recommended_movies_poster,release_dates=recommended_movies_release_dates,current_movie=movies_name,current_movie_overview=current_movie_overview,current_movie_genre=current_movie_genre,current_movie_release_date=current_movie_release_date,current_movie_cast=current_movie_cast,current_movie_poster=current_movie_poster)
            except Exception as e:
                error={'error':e}
                return render_template("indianMovies.html",movie_names=indian_movies_names)
    else:
        print("Session not found")
        return redirect(url_for("signin"))


# Indian Movie Recommendations
@app.route('/indianrec', methods=['GET', 'POST'])
def indianrec():
    return render_template("indianrec.html",movie_names=indian_movies_names)






#----------------------------------------------- Web Series Recommendation-----------------------------------------





web=pickle.load(open('model/web_series/web_series_last.pkl','rb'))
similarity=pickle.load(open('model/web_series/web_series_similarity.pkl','rb'))


def db_connect_web_series(db_name):
    conn = None
    try:
        conn = sqlite3.connect("./model/web_series/"+db_name+".sqlite")
    except sqlite3.error as e:
        print(e)
    return conn

conn = db_connect_web_series("web_series")
cursor = conn.cursor()
cursor.execute("Select * from web_series")
web_series_result = cursor.fetchall()
conn.close()

def fetch_webShow_details(show_index):
    show_id=""
    desc=""
    actors=""
    genre=""
    for row in web_series_result:
        if row[0]==show_index:
            show_id=row[2]
            desc=row[4]
            genre=row[3].split("$")
            actors=list(row[5].split("$"))
    return show_id,desc,genre,actors

# Function to recommend web series

def web_show_recommend(web_show):
    show_index=""
    for row in web_series_result:
        if row[1]==web_show:
            show_index=row[0]
    web_show_id,current_web_show_overview,current_web_show_genre,current_web_show_cast=fetch_webShow_details(show_index)
    current_web_show_poster=fetch_poster_webShow(web_show_id)
    current_web_show_release_date=fetch_release_date_webShow(web_show_id)
    #------------ Cosine Similarity Method -----------------#

    web_index=web[web['title']==web_show].index[0]
    distances=sorted(list(enumerate(similarity[web_index])),reverse=True,key=lambda x:x[1])
    recommended_web_show_name=[]
    recommended_web_show_poster=[]
    recommended_web_show_release_dates=[]
    for i in distances[1:9]:
        web_show_id=web.iloc[i[0]].url
        recommended_web_show_poster.append(fetch_poster_webShow(web_show_id))
        recommended_web_show_release_dates.append(fetch_release_date_webShow(web_show_id))
        recommended_web_show_name.append(web.iloc[i[0]].title)
    return recommended_web_show_name,recommended_web_show_poster,recommended_web_show_release_dates,current_web_show_overview,current_web_show_release_date,current_web_show_genre,current_web_show_cast,current_web_show_poster


    #------------ Annoy Method -----------------#

    # u = AnnoyIndex(3200, 'angular')
    # u.load('./model/web_series/vectors.ann')
    # web_series_list = (u.get_nns_by_item(show_index, 8))[1:8]
    # recommended_web_show_name=[]
    # recommended_web_show_poster=[]
    # recommended_web_show_release_dates=[]
    # for i in web_series_list:
    #     web_show_id=""
    #     web_series_name=""
    #     for row in web_series_result:
    #         if row[0]==i:
    #             web_show_id=row[2]
    #             web_series_name=row[1]
        # recommended_web_show_poster.append(fetch_poster_webShow(web_show_id))
        # recommended_web_show_release_dates.append(fetch_release_date_webShow(web_show_id))
        # recommended_web_show_name.append(web_series_name)
    # return recommended_web_show_name,recommended_web_show_poster,recommended_web_show_release_dates,current_web_show_overview,current_web_show_release_date,current_web_show_genre,current_web_show_cast,current_web_show_poster

# Providing Web Series names in list

web_series_names=[]
for row in web_series_result:
    web_series_names.append(row[1])

# Web Series
@app.route('/web_series/<web_show>')

def web_series(web_show):
    if "user" in session:
            try:
                web_shows=web_show
                recommended_web_show_name,recommended_web_show_poster,recommended_web_show_release_dates,current_web_show_overview,current_web_show_release_date,current_web_show_genre,current_web_show_cast,current_web_show_poster=web_show_recommend(web_shows)
                return render_template("web_series.html",recommendations=recommended_web_show_name,web_series_names=web_series_names,poster=recommended_web_show_poster,release_dates=recommended_web_show_release_dates,current_web_show=web_shows,current_web_show_overview=current_web_show_overview,current_web_show_genre=current_web_show_genre,current_web_show_release_date=current_web_show_release_date,current_web_show_cast=current_web_show_cast,current_web_show_poster=current_web_show_poster)
            except Exception as e:
                error={'error':e}
                return render_template("web_series.html",web_series_names=web_series_names)
    else:
        print("Session not found")
        return redirect(url_for("signin"))


# Web Series Recommendations
@app.route('/web_series_rec', methods=['GET', 'POST'])
def web_series_rec():
    return render_template("web_series_rec.html",web_series_names=web_series_names)


if __name__ == "__main__":
    app.run(debug=True)


