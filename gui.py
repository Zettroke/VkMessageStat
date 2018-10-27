from tkinter import Tk, RIGHT, LEFT, TOP, DISABLED, NORMAL, Toplevel, Menu, INSERT, Listbox, END, VERTICAL, Y, BOTH, Text, X, ALL, DoubleVar
from tkinter.ttk import Entry, Button, Label, Style, Frame, Scrollbar, Progressbar

import sys
import webbrowser
import os
import requests
import re
import traceback
from threading import Thread

from vk_messages_stats import stats

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

class GUI:
    def __init__(self):
        self.root = Tk()
        self.root.title("VkMessageStat")
        self.root.iconbitmap(os.path.join(base_dir, "icon.ico"))
        self.root.geometry('661x617')
        Style().configure("Login.TLabel", foreground="#777777", font=("Arial", 12))

        Style().configure("TFrame", bg="#ff0000")

        self.login_status_label = Label(self.root, text="Проверка логина...", style="Login.TLabel")
        self.login_status_label.pack(side=TOP, pady=10)

        self.login_button = Button(self.root, text='Войти', state=DISABLED, command=self.proceed_login)
        self.login_button.pack()
        self.root.after(50, self.login_check)

        self.is_logged_in = False
        self.access_token = ''
        self.root.bind("<Return>", self.bnd)

        self.current_progress = 0
        self.progress_value = DoubleVar()

        self.users = []

        self.root.mainloop()

    def bnd(self, event=None):
        self.t.configure(state=NORMAL)
        self.t.insert(END, 'enter\n')
        self.t.yview_moveto(1)
        self.t.configure(state=DISABLED)

    def login_check(self):
        try:
            need_token = True
            if os.path.exists('access_token'):
                access_token = open('access_token', 'r').read()
                r = requests.get(
                    "https://api.vk.com/method/users.get?v=5.78&access_token={access_token}".format(
                        access_token=access_token)
                )
                if 'response' in r.json().keys():
                    need_token = False
                    self.access_token = access_token

            if need_token:
                Style().configure("Login.TLabel", foreground="#f44336")
                self.login_status_label.configure(text="Неудалось войти")
                self.login_button.configure(state=NORMAL)
            else:
                self.logged_in()
        except Exception as e:
            traceback.print_exc(file=open("VkStatError.txt", "w", encoding='utf-8'))
            Style().configure("Login.TLabel", foreground="#f44336")
            self.login_status_label.configure(text='Произошла неизветстная ошибка при проверке логина.\n'
                                                   'Отчет сохренен в фале VkStatError.txt\n'
                                                   'Попробуйте снова')

    def proceed_login(self):
        t = Toplevel(self.root)
        t.iconbitmap(os.path.join(base_dir, "icon.ico"))
        t.title("Login")
        Style().configure("Error.TLabel", foreground="#f44336")
        link_check = re.compile('https:\/\/oauth\.vk\.com\/blank\.html#access_token=[a-z0-9]*&expires_in=[0-9]*&user_id=[0-9]*')

        l = Label(t, text=
        """
Сейчас откроеться ваш браузер. Вам будет нужно войти вконтакте и разрешить приложению читать ваши сообщения
Скопируйте и вставьте ссылку на страницу, на которую вас перенаправило, после входа Вконтакте.
Она будет вида https://oauth.vk.com/blank.html#access_token=....&expires_in=....&user_id=....
        """)
        l.pack()
        e = Entry(t, width=75)
        e.pack(pady=5, padx=10)

        err = Label(t, style="Error.TLabel")
        err.pack()

        def try_login_link():
            s = e.get()
            err.configure(text='')
            if not link_check.match(s):
                err.configure(text="То что вы вставили не похоже на нужную ссылку.")
                return
            else:
                token = ''
                params = s.split('#')[1]
                pairs = params.split('&')
                for p in pairs:
                    k, v = p.split('=')
                    if k == 'access_token':
                        token = v
                r = requests.get(
                    "https://api.vk.com/method/users.get?v=5.78&access_token={access_token}".format(
                        access_token=token)
                )
                if 'response' in r.json():
                    self.access_token = token
                    t.destroy()
                    self.logged_in()
                else:
                    err.configure(text="Токен некорректен. Попобуйте войти заново.")

        b = Button(t, text="Войти", command=try_login_link)
        b.pack(pady=5)

        def paste():
            e.insert(INSERT, self.root.clipboard_get())

        popup = Menu(t, tearoff=0)
        popup.add_command(label="Paste", command=paste)

        def do_popup(event):
            try:
                popup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                popup.grab_release()

        e.bind("<Button-3>", do_popup)

        self.root.after(200, lambda: webbrowser.open("https://zettroke.github.io/VkMessageStat/login_page"))

    def logged_in(self):
        Style().configure("Login.TLabel", foreground="#4caf50")
        open('access_token', 'w').write(self.access_token)
        r = requests.get(
            "https://api.vk.com/method/users.get?v=5.78&access_token={access_token}".format(
                access_token=self.access_token)
        )
        u = r.json()['response'][0]

        self.login_status_label.configure(text="Удалось войти как {} {}".format(u['first_name'], u['last_name']))
        self.login_button.configure(state=DISABLED)

        r = requests.get(
            "https://api.vk.com/method/messages.getConversations?v=5.78&access_token={access_token}&count=100".format(
                access_token=self.access_token)
        )
        peer_list = []
        conv_list = r.json()['response']['items']
        for c in conv_list:
            peer = c['conversation']['peer']
            if peer['type'] == 'user':
                peer_list.append(str(peer['id']))

        r = requests.get(
            "https://api.vk.com/method/users.get?v=5.78&access_token={access_token}&user_ids={users_id}".format(
                access_token=self.access_token,
                users_id=','.join(peer_list)
            )
        )
        self.users = r.json()['response']
        Frame(self.root).pack(pady=10)
        l = Label(self.root, text="Выбериет диалог:")
        l.pack()

        frame = Frame(self.root)
        scrollbar = Scrollbar(frame, orient=VERTICAL)
        self.listbox = Listbox(frame, yscrollcommand=scrollbar.set, font=("Arial", 14))
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.listbox.pack(side=LEFT, fill=BOTH, expand=1)
        frame.pack()
        self.start_button = Button(self.root, text="Выбрать", command=self.listbox_select)
        self.start_button.pack(pady=10)

        for i in self.users:
            self.listbox.insert(END, i['first_name'] + ' ' + i['last_name'])
        self.listbox.bind("<Double-Button-1>", self.listbox_select)

        frame1 = Frame(self.root)
        frame1.pack()
        scrollbar1 = Scrollbar(frame1, orient=VERTICAL)
        self.t = Text(frame1, takefocus=False, yscrollcommand=scrollbar1.set, height=13)
        scrollbar1.config(command=self.t.yview)
        scrollbar1.pack(side=RIGHT, fill=Y)
        self.t.pack(fill=X)
        self.t.configure(state=DISABLED)

        self.prog_bar = Progressbar(self.root, maximum=10000, mode='determinate', variable=self.progress_value)
        self.prog_bar.pack(fill=X)

    def listbox_select(self, event=None):
        if self.listbox.curselection():
            user = self.users[self.listbox.curselection()[0]]
            self.start_button.configure(state=DISABLED)

            self.start_stats(user['id'])

    def start_stats(self, user_id):
        self.t.configure(state=NORMAL)
        self.t.delete('1.0', END)
        self.t.configure(state=DISABLED)

        t = Thread(target=stats.make_stats,
                   args=(self.access_token, user_id, ['vk_basic_stats.vk_base_stats']),
                   kwargs=dict(post_message_func=self.message, post_progress_func=self.progress, callback=self.stat_done),
                   daemon=True)
        t.start()

    def stat_done(self):
        self.start_button.configure(state=NORMAL)
        webbrowser.open("file:///" + os.path.join(os.path.abspath(os.getcwd()), 'result', 'result.html'))

    def progress(self, frac):
        self.progress_value.set(frac*10000)

    def message(self, msg):
        def f(msg):
            self.t.configure(state=NORMAL)
            self.t.insert(END, msg)
            self.t.configure(state=DISABLED)

        self.root.after(10, f, msg)


if __name__ == '__main__':
    g = GUI()
