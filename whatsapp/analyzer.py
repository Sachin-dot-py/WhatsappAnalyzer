#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
import re
import emoji
from collections import Counter
from wordcloud import WordCloud


class WhatsAppAnalyzer():
    """ Analyze a WhatsApp chat and get statistics """
    def __init__(self, file=None, content=None):
        """
        Either filename or file contents is required to initialise the class
        """
        self.file = None
        if not file and not content:
            raise AssertionError("No filename or content passed")
        if file:
            self.file = file
            with open(file) as f:
                content = f.read()
        try:
            self.name = re.search(r'"(.*?)"',
                                  content.splitlines()[1]).group().strip(r'"')
        except:
            if 'WhatsApp Chat with ' in file:
                self.name = file.strip(".txt").split("WhatsApp Chat with ")[1]
            self.name = "WhatsApp Group"  # Default if unable to get chat name
        self.df = self.parse_chat(content)
        self.userdf = self.parse_user()
        self.datedf = self.parse_date()
        self.daydf = self.parse_day()
        self.hourdf = self.parse_hour()
        self.worddf = self.parse_words()
        self.emojidf = self.parse_emojis()
        self.messagedf = self.parse_messages()

    def parse_chat(self, content) -> pd.DataFrame:
        """ Parses content and returns a Dataframe with contact, datetime object and message """
        lines = content.splitlines()
        if "end-to-end encryption" in lines[0]:
            lines.pop(0)  # Remove message about end-to-end encryption
        messages = []
        for line in lines:
            try:
                system_message = False
                media = 0
                deleted = 0
                date_str = line.split(' - ')[0]
                contact = line.split(' - ')[1].split(':')[0]
                if len(line.split(":")) == 2:
                    system_message = True
                    continue  # Automatic messages such as "XX person left", "XX added YY" etc.
                message = ":".join(line.split(':')[2:]).lstrip(' ')
                if message == "<Media omitted>":
                    media = 1
                    message = ""
                if message == "This message was deleted" or message == "You deleted this message":
                    deleted = 1
                    message = ""
                emojis = emoji.emoji_lis(message)
                if emojis:
                    emojis = "".join([item['emoji'] for item in emojis])
                else:
                    emojis = ""
                timestamp = datetime.strptime(date_str, "%d/%m/%Y, %I:%M %p")
                date = datetime(year=timestamp.year,
                                month=timestamp.month,
                                day=timestamp.day)
                day = timestamp.strftime("%A")
                hour = timestamp.hour
                words = len(message.split())
                letters = len(message.replace(" ", "").replace("\n", ""))
            except:  # For multi-line messages
                prev_msg = messages[-1].get('message') + "\n"
                new_msg = prev_msg + line
                letters = len(new_msg.replace(" ", "").replace("\n", ""))
                emojis = emoji.emoji_lis(new_msg)
                if emojis:
                    emojis = "".join([item['emoji'] for item in emojis])
                else:
                    emojis = ""
                messages[-1]['message'] = new_msg
                messages[-1]['words'] = len(new_msg.split())
                messages[-1]['letters'] = letters
                messages[-1]['emojis'] = emojis
                messages[-1]['emoji_num'] = len(list(emojis))
            else:
                if not system_message:
                    message_data = {
                        'contact': contact,
                        'timestamp': timestamp,
                        'date': date,
                        'day': day,
                        'hour': hour,
                        'media': media,
                        'deleted': deleted,
                        'message': message,
                        'words': words,
                        'letters': letters,
                        'emojis': emojis,
                        'emoji_num': len(list(emojis))
                    }
                    messages.append(message_data)
        df = pd.DataFrame(messages)
        return df

    def parse_user(self) -> dict:
        """ Parse dataframe to get user dataframe with count of messages, media and more per user """
        user_table = {k: table for k, table in self.df.groupby("contact")}
        return user_table

    def parse_date(self) -> dict:
        """ Parse dataframe to get a dictionary of number of messages on each day """
        return dict(self.df['date'].value_counts())

    def parse_day(self) -> dict:
        """ Parse dataframe to get a dictionary of number of messages by day of the week """
        return dict(self.df['day'].value_counts())

    def parse_hour(self) -> dict:
        """ Parse dataframe to get a dictionary of number of messages by hour of the day """
        return dict(self.df['hour'].value_counts())

    def parse_words(self) -> dict:  # TODO Remove stopwords
        """ Parse dataframe to get dictionary with each word and its number of uses """
        worddf = self.df.message.str.split(expand=True).stack()
        worddf = worddf.str.lower().str.strip("(.-*!?_:')")
        worddf = dict(worddf.value_counts())
        return worddf

    def parse_emojis(self) -> dict:
        """ Parse dataframe to get a dictionary with each emoji and its number of uses """
        emojis = list(self.df.emojis.sum())
        emojidf = Counter(emojis).most_common()
        return emojidf

    def parse_messages(self) -> dict:
        """ Parse dataframe to get a dictionary of number of messages per contact """
        messagedf = {user: len(self.userdf[user]) for user in self.users}
        return messagedf

    @property
    def users(self) -> list:
        """ Get a list of users in the group """
        return self.userdf.keys()

    @property
    def most_active_date(self) -> tuple:
        """ Gets date which was most active (most number of messages) """
        date, messages = next(iter(self.datedf.items()))
        date = date.strftime("%B %d, %Y")
        return (date, messages)

    @property
    def most_active_day(self) -> str:
        """ Get weekday which was most active (most number of messages) """
        return self.df['day'].mode()[0]

    @property
    def highest_messages(self) -> str:
        """ Get name of user who has sent the most number of messages """
        return self.df['contact'].mode()[0]

    @property
    def highest_words(self) -> str:
        """ Get name of user who has sent the longest message (highest number of words) """
        highest = self.df.iloc[self.df['words'].argmax()]
        return (highest['contact'], highest['words'])

    @property
    def first_message_date(self) -> pd.Timestamp:
        """
        Get date of first message as a pandas Timestamp object
        """
        first = self.df.at[0, 'timestamp']
        return first

    @property
    def last_message_date(self) -> pd.Timestamp:
        """
        Get date of last message as a pandas Timestamp object
        """
        last = self.df.at[len(self.df) - 1, 'timestamp']
        return last

    @property
    def total_days(self) -> int:
        """
        Get total number of days between first and last message
        """
        days = (self.last_message_date - self.first_message_date).days
        return days

    @property
    def total_messages(self) -> int:
        """ Get total number of messages """
        return len(self.df)

    @property
    def total_emojis(self) -> int:
        """ Get total number of emojis """
        return self.df['emoji_num'].sum()

    @property
    def total_words(self) -> int:
        """ Get total number of words """
        return self.df['words'].sum()

    @property
    def total_letters(self) -> int:
        """ Get total number of letters """
        return self.df['letters'].sum()

    @property
    def total_media(self) -> int:
        """ Gets total number of media """
        return self.df['media'].sum()

    @property
    def total_deleted(self) -> int:
        """ Gets the total number of deleted messages """
        return self.df['deleted'].sum()

    @property
    def wordcloud(self):
        """ Creates and returns the wordcloud as a PIL image """
        text = self.df.message.sum()
        wordcloud = WordCloud().generate(text)
        image = wordcloud.to_image()
        return image

    @property
    def average_messages(self) -> int:
        """ Gets average number of messages per day """
        return int(self.total_messages / self.total_days)

    def get_user(self, name) -> dict:
        """ Returns dict of statistics for the given user name """
        try:
            user = self.userdf[name]
        except:
            raise AssertionError(f"User {name} does not exist")
        deleted = user['deleted'].sum()
        media = user['media'].sum()
        words = user['words'].sum()
        letters = user['letters'].sum()
        emojis = user['emoji_num'].sum()
        emoji_list = list(user.emojis.sum())
        fav_emoji, num_uses = Counter(emoji_list).most_common()[0]
        messages = len(user) - media
        words_per_message = int(words / messages)
        letters_per_word = int(letters / words)
        userdict = {
            'messages': messages,
            'media': media,
            'deleted': deleted,
            'emojis': emojis,
            'fav_emoji': (fav_emoji, num_uses),
            'words': words,
            'letters': letters,
            'words_per_message': words_per_message,
            'letters_per_word': letters_per_word
        }
        return userdict


if __name__ == "__main__":
    file = 'sample_chat/sample_chat.txt'  # Chat data exported from WhatsApp
    wa = WhatsAppAnalyzer(file)
