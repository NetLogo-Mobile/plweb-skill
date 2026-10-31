"""Minimal local login. Do not inspect this window while a user enters credentials."""
import argparse
import queue
import threading
import tkinter as tk
from tkinter import ttk
from community_client import CommunityClient, DOMAINS, CommunityError
from session_store import SessionStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--domain', choices=DOMAINS, default=DOMAINS[0])
    parser.add_argument('--version', type=int, default=2411)
    args = parser.parse_args()
    root = tk.Tk()
    root.title('物理实验室登录')
    root.resizable(False, False)
    frame = ttk.Frame(root, padding=16)
    frame.grid()
    ttk.Label(frame, text='账号').grid(row=0, column=0, padx=(0, 8), pady=6)
    account = ttk.Entry(frame, width=30)
    account.grid(row=0, column=1, pady=6)
    ttk.Label(frame, text='密码').grid(row=1, column=0, padx=(0, 8), pady=6)
    password = ttk.Entry(frame, show='•', width=30)
    password.grid(row=1, column=1, pady=6)
    status = tk.StringVar(value='仅保存加密会话，不保存密码。')
    ttk.Label(frame, textvariable=status).grid(row=3, column=0, columnspan=2, pady=(8, 0))
    completed = queue.Queue()

    def worker(login, secret):
        try:
            store = SessionStore()  # Fail before logging in if storage is unavailable.
            api = CommunityClient(domain=args.domain, version=args.version)
            api.login(login, secret)
            api.save(store)
            completed.put((True, '登录成功，会话已安全保存。'))
        except CommunityError as error:
            completed.put((False, f'登录失败：{error.kind} ({error.status})'))
        except Exception:
            completed.put((False, '无法登录或安全保存，请检查网络和系统凭据库。'))
        finally:
            login = secret = None  # No plaintext persistence or diagnostic output.

    def poll():
        try:
            ok, message = completed.get_nowait()
        except queue.Empty:
            root.after(100, poll)
            return
        status.set(message)
        if ok:
            account.delete(0, tk.END)
            root.after(900, root.destroy)
        else:
            button.state(['!disabled'])

    def submit():
        login, secret = account.get().strip(), password.get()
        password.delete(0, tk.END)
        if not login or not secret:
            status.set('请输入账号和密码。')
            return
        button.state(['disabled'])
        status.set('正在登录…')
        threading.Thread(target=worker, args=(login, secret), daemon=True).start()
        root.after(100, poll)

    button = ttk.Button(frame, text='登录', command=submit)
    button.grid(row=2, column=0, columnspan=2, pady=(8, 0))
    root.bind('<Return>', lambda event: submit() if 'disabled' not in button.state() else None)
    account.focus()
    root.mainloop()


if __name__ == '__main__':
    main()
