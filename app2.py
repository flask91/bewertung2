###########
# Imports #
###########

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from spellchecker import SpellChecker
import re
import textstat
from textblob_de import TextBlobDE as TextBlob

from sqlalchemy import desc

from functions.functions import zufallswort

# store in requirements:
# pip freeze > requirements.txt

#####################
# App Konfigurieren #
#####################
app = Flask(__name__)
app.secret_key = 'Key%S3creTk3Y!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///prototyp2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#############
# Datenbank #
#############
'''
Tabelle:
- User > enthält Backgroundinfo über Reviewer/Tester + Einordnung der Expertise + Verweis auf Reviews
- Review > enthält generelle Infos über Review (Titel, Datum, Produktart, Rating, Verweis auf Argumente)
- Argumente > enthält die Pro und Contra Argumente (Eigenschaft + Textuelle beschreibung)

# https://docs.sqlalchemy.org/en/14/orm/basic_relationships.html#one-to-one
'''

# SQLAlchemy Datenbank initialisieren
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'user'
    # Persönliche Daten:
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), default="anonym")
    email = db.Column(db.String(20), default='N/A')
    alter = db.Column(db.String(20), default="Nicht angegeben")  # Altersgruppen
    code = db.Column(db.String(6), nullable=False, default="abc123")  # Persönlicher Code für User-Zuordnung
    gender = db.Column(db.Integer, nullable=False, default=0)  # 0=keine Angabe 1=weibl 2=männl, 3=other
    bildung = db.Column(db.Integer)  # 0=Kein, 1=Hauptschule, 2=Weiterführende Schule, 3= Abitur, 4= Bachelor 5=Master

    #  Erfahrung als Summe der Erfahrungswerte
    erfahrung = db.Column(db.Integer, nullable=False, default=0)
    # Erfahrungswerte:
    anz_best = db.Column(db.Integer, nullable=False, default=0)  # Wie oft online bestellt?
    anz_les = db.Column(db.Integer, nullable=False, default=0)  # Wie oft bewertungen gelesen?
    anz_bew_prod = db.Column(db.Integer, default=0)  # wie oft insgesamt bewertet?
    anz_bew_buch = db.Column(db.Integer)  # wie oft Buch bewertet?
    anz_bew_reise = db.Column(db.Integer)  # wie oft Reise bewertet?
    anz_bew_serie = db.Column(db.Integer)  # wie oft Serie bewertet?
    anz_bew_essen = db.Column(db.Integer)  # wie oft Essen bewertet?
    self_expert = db.Column(db.Integer, nullable=False, default=3)  # Einschätzung der eigenen Expertiese

    # Feedback Rückmeldung
    feedback = db.Column(db.Text, nullable=False, default="")

    reviews = db.relationship('Review', backref="user")  # backref, fake column in anderer


# Datenbank definieren.
class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.now())

    product_art = db.Column(db.Integer, nullable=False, default=0)
    product = db.Column(db.String(100), nullable=False, default="title")  # Welches Buch/Reiseort

    rating = db.Column(db.Integer, nullable=False, default=0)
    feel = db.Column(db.Text, nullable=False, default="feel")
    content = db.Column(db.Text, nullable=False, default="")

    fazit = db.Column(db.Text, nullable=False, default="noch leer")

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


#########
# Views #
#########


# Startseite mit allgemeinen Infos
@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


# Tester Hintergrundinformationen
@app.route('/start', methods=['GET', 'POST'])
def start():
    if request.method == 'POST':
        usr_name = request.form['name']
        usr_email = request.form['email']
        usr_bdate = request.form['alter']
        usr_gender = request.form['gender']
        usr_bildung = request.form['bildung']
        usr_anz_best = request.form['anz_best']
        usr_anz_les = request.form['anz_les']
        usr_anz_bew_prod = request.form['anz_bew_prod']
        usr_anz_bew_buch = request.form['anz_bew_buch']
        usr_anz_bew_reise = request.form['anz_bew_reise']
        usr_anz_bew_serie = request.form['anz_bew_serie']
        usr_anz_bew_essen = request.form['anz_bew_essen']
        usr_self_expert = request.form['self_expert']
        usr_code = zufallswort(6)
        new_user = User(name=usr_name,
                        email=usr_email,
                        alter=usr_bdate,
                        gender=usr_gender,
                        bildung=usr_bildung,
                        anz_best=usr_anz_best,
                        anz_les=usr_anz_les,
                        anz_bew_buch=usr_anz_bew_buch,
                        anz_bew_prod=usr_anz_bew_prod,
                        anz_bew_reise=usr_anz_bew_reise,
                        anz_bew_serie=usr_anz_bew_serie,
                        anz_bew_essen=usr_anz_bew_essen,
                        self_expert=usr_self_expert,
                        code=usr_code)
        db.session.add(new_user)

        # Erfahrung summieren:
        # usr = neuer User
        # update von der Erfahrung durch Summe der Angaben...
        # TODO Formel anpassen..
        usr = User.query.order_by(User.id.desc()).first()
        sum_erfahrung = \
            usr.anz_best + usr.anz_bew_prod + usr.anz_bew_reise + usr.anz_bew_essen + usr.anz_bew_serie + usr.anz_les \
            + usr.self_expert
        usr.erfahrung = sum_erfahrung

        db.session.commit()

        return redirect(url_for('neu', user=usr.code))

    return render_template('start.html')


# Neuer Post beginnt mit der Auswahl der zu bewertenden "Produkte"
@app.route('/neu/<user>', methods=['GET', 'POST'])
def neu(user):
    usr = User.query.filter_by(code=user).first()

    if request.method == 'POST':
        if request.form.get("Buch"):
            prod = 0
            new_post = Review(product_art=prod, user_id=usr.id)
            db.session.add(new_post)
            # commit also spiechern auch nach session
            db.session.commit()
            return redirect(url_for('product', user=usr.code))
        if request.form.get("Reise"):
            prod = 1
            new_post = Review(product_art=prod, user_id=usr.id)
            db.session.add(new_post)
            # commit also spiechern auch nach session
            db.session.commit()
            return redirect(url_for('product', user=usr.code))
        if request.form.get("Serie"):
            prod = 2
            new_post = Review(product_art=prod, user_id=usr.id)
            db.session.add(new_post)
            # commit also spiechern auch nach session
            db.session.commit()
            return redirect(url_for('product', user=usr.code))
        if request.form.get("Essen"):
            prod = 3
            new_post = Review(product_art=prod, user_id=usr.id)
            db.session.add(new_post)
            # commit also spiechern auch nach session
            db.session.commit()
            return redirect(url_for('product', user=usr.code))
    return render_template('neu.html', user=usr.code)


# Produktauswahl: - Gesamteindruck"
@app.route('/product/<user>', methods=['GET', 'POST'])
def product(user):
    usr = User.query.filter_by(code=user).first()
    post = Review.query.filter_by(user_id=usr.id).order_by(desc(Review.id)).first()

    art = ""
    art1 = ""
    if post.product_art == 0:
        art = "Buch"
        art1 = "eines Buches"
    if post.product_art == 1:
        art = " Reise"
        art1 = "einer Reise"
    if post.product_art == 2:
        art = " Serie"
        art1 = "einer Serie"
    if post.product_art == 3:
        art = " Essenslieferung"
        art1 = "der letzten Essenslieferung"

    if request.method == 'POST':
        # TODO Buch suche API einbauen?
        post.product = request.form['product']
        post.rating = request.form['rating']
        post.feel = request.form['feel']
        print(post.feel)
        db.session.commit()
        return redirect(url_for('bewertung', user=usr.code))
    return render_template('product.html', user=usr.code, post=post,
                           art=art, art1=art1, usr=usr, len_usr=len(usr.name))


@app.route('/bewertung/<user>', methods=['GET', 'POST'])
def bewertung(user):
    usr = User.query.filter_by(code=user).first()
    post = Review.query.filter_by(user_id=usr.id).order_by(desc(Review.id)).first()

    # Wörter zählen
    # https://www.python-forum.de/viewtopic.php?t=31569
    wortanzahl = sum(1 for space in re.finditer(r"[^\s]+", post.content))

    # Lesbarkeitsindex textstat: Deutsch
    # https://pypi.org/project/textstat/
    textstat.set_lang('de')
    fr = textstat.flesch_reading_ease(post.content)  # FR-Index gewählt, weil auch auf Deutsch verfügbar

    # Sentiment Berechnung  mit Textblob
    # https://textblob-de.readthedocs.io/en/latest/
    blob = TextBlob(post.content)
    senti = blob.sentiment  # Sentimentermittlung durch Textblob

    # Anzahl nomen als Indikator für Bewertete Eigenschaften
    # evtl. in Prototyp 2
    # blob2 = TextBlob(str(post.content))
    # tags = blob2.tags
    # nomen = []
    # for t in tags:
    #    if t[1] == "NN":
    #        nomen.append(t)

    if request.method == 'POST':
        post.rating = request.form['rating']
        post.content = request.form['content']
        post.feel = request.form['title']
        db.session.commit()
        return redirect(url_for('bewertung', user=usr.code))
    else:
        return render_template('bewertung.html', user=usr.code, post=post,
                               wortanzahl=wortanzahl, fr=fr,
                               senti=(round(senti.polarity, 3)), subj=senti.subjectivity)


# Fazit hinzufügen:
@app.route('/fazit/<user>', methods=['GET', 'POST'])
def fazit(user):
    usr = User.query.filter_by(code=user).first()
    post = Review.query.filter_by(user_id=usr.id).order_by(desc(Review.id)).first()

    if request.method == 'POST':
        post.fazit = request.form['fazit']
        post.content = post.content + "\n\n" + post.fazit
        db.session.commit()
        return redirect(url_for('vorschau', user=usr.code))
    return render_template('fazit.html', user=usr.code, post=post)


@app.route('/vorschau/<user>', methods=['GET', 'POST'])
def vorschau(user):
    usr = User.query.filter_by(code=user).first()
    post = Review.query.filter_by(user_id=usr.id).order_by(desc(Review.id)).first()

    if request.method == 'POST':
        post.content = request.form['content']
        db.session.commit()
        return redirect(url_for('feedback', user=usr.code))
    return render_template('vorschau.html', user=usr.code, post=post)


@app.route('/feedback/<user>', methods=["POST", "GET"])
def feedback(user):
    usr = User.query.filter_by(code=user).first()
    post = Review.query.filter_by(user_id=usr.id).order_by(desc(Review.id)).first()

    review = post.content.replace("\n", "<br />")
    if request.method == 'POST':
        usr.feedback = request.form['feedback']
        db.session.commit()
        # Übergabe parameter Code
        return redirect(url_for('danke', user=usr.code))
    return render_template('feedback.html', post=post, review=review, usr=usr)


@app.route('/danke/<user>', methods=("POST", "GET"))
def danke(user):
    usr = User.query.filter_by(code=user).first()
    # TODO Dankeschön für die Teilname einbauen?? Gutschein??
    return render_template('danke.html', usr=usr, user=usr.code)


if __name__ == "__main__":
    app.run(debug=True)
