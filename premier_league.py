import argparse
import re
import requests
import smtplib, ssl
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from getpass import getpass
from urllib.parse import urljoin


def validate_email_argument(email):
    string_pattern = r'''(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])'''
    try:
        pattern = re.compile(string_pattern)
        assert pattern.match(email) is not None
        return email
    except AssertionError:
        raise argparse.ArgumentTypeError('Invalid e-mail')


def validate_date_argument(date):
    try:
        return datetime.strptime(date, '%Y-%m-%d')
    except:
        raise argparse.ArgumentTypeError('Invalid date format, it must be YYYY-MM-DD')


def validate_date_range(initial_date, final_date):
    try:
        assert (final_date - initial_date).days <= 31
    except AssertionError:
        raise argparse.ArgumentError(None, 'Invalid date range. Max range need to be 31 days.')


def get_url():
    url = urljoin('https://site.api.espn.com/', ('apis/site/v2/sports/soccer/eng.1/scoreboard'
    '?lang=pt&region=br&calendartype=whitelist&limit=100&showAirings=true&'
    f'dates={str(args.initial_date.date()).replace("-", "")}-'
    f'{str(args.final_date.date()).replace("-", "")}&tz=America%2FNew_York&league=eng.1'))
    return url


def email_template(json):
    html = """
        <style>
            * {
                font-family: "Courier New", sans-serif;
            }

            table {
                text-align: center;
                width: 100%;
            }

            .defeat {
                background-color: #B22222;
                color: #EEE;
                padding: 5px;
            }

            .win {
                background-color: #006400;
                color: #EEE;
                padding: 5px;
            }

            .draw {
                background-color: #CCC;
                color: black;
                padding: 5px;
            }

            .score {
                font-weight: bold;
                font-size: 36px;
            }

            tr.spacer td {
                padding-bottom: 60px;
            }
        </style>
        <table cellspacing="0" cellpadding="10" border="0">
    """

    for event in json.get('events', []):
        competitions = event.get('competitions')[0]

        home_team = competitions['competitors'][0]
        away_team = competitions['competitors'][1]

        types = {
            'D': '<span class="defeat">{}</span>',
            'E': '<span class="draw">{}</span>',
            'V': '<span class="win">{}</span>',
        }

        home_form = ''.join(map(lambda form: types[form].format(form), home_team['form']))
        away_form = ''.join(map(lambda form: types[form].format(form), away_team['form']))

        match_day = competitions['date'].replace('T', ' ').replace('Z', 'h')

        html += f"""
            <tr>
                <td colspan="5">{competitions['venue']['fullName']} - {match_day}</td>
            </tr>
            <tr>
                <td>
                    <img height="60" src="{home_team['team']['logo']}" >
                    <h3>{home_team['team']['displayName']}</h3>
                    <span>{home_form}</span>
                </td>
                <td class="score">{home_team['score']}</td>
                <td>X</td>
                <td class="score">{away_team['score']}</td>
                <td>
                    <img height="60" src="{away_team['team']['logo']}" >
                    <h3>{away_team['team']['displayName']}</h3>
                    <span>{away_form}</span>
                </td>
            </tr>
        """

        for link in event.get('links'):
            if link['text'] == 'Resumo':
                html += f"""
                    <tr class="spacer">
                        <td colspan="5">
                            <a href="{link['href']}" target="_blank">Resumo da Partida</a>
                        </td>
                    </tr>
                """
    html += "</table>"
    return html


def send_email(email, host, html):

    hosts = {
        'gmail': {
            'host': 'smtp.gmail.com',
            'port': 587
        },
        'outlook': {
            'host': 'smtp-mail.outlook.com',
            'port': 587
        }
    }

    body = MIMEText(html, 'html')

    message = MIMEMultipart('alternative')
    message['Subject'] = 'Premier League Results'
    message['From'] = email
    message['To'] = email
    message.attach(body)

    password = getpass('Enter your e-mail password: ')
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(**hosts[host]) as smtp:
            smtp.starttls(context=context)
            smtp.login(email, password)
            smtp.sendmail(
                email, email, message.as_string()
            )
        print('E-mail has been sent!')
    except Exception as e:
        print(f'Error trying to send the e-mail. Please try again. Error: {e}')


parser = argparse.ArgumentParser(prog=__file__, description='Welcome to the Premier League! For those who loves PL but don\'t have time for it :(')
parser.add_argument('--email', '-e', type=str, required=True, help='E-mail that results will be sent')
parser.add_argument('--initial-date', '-id', required=True, type=validate_date_argument, help='The initial date that you want the results')
parser.add_argument('--final-date', '-fd', required=False, type=validate_date_argument, default=str(datetime.now().date()))
parser.add_argument('--host', choices=['gmail', 'outlook'], required=True)

if __name__ == '__main__':
    args = parser.parse_args()
    validate_date_range(args.initial_date, args.final_date)

    url = get_url()
    
    resp = requests.get(url)
    html = email_template(resp.json())
    send_email(args.email, args.host, html)
