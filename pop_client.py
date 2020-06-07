import base64
from socket import socket, AF_INET, SOCK_STREAM
import ssl
import sys
import quopri
import re

CONTENT_TRANSFER_ENCODINGS = {'quoted-printable': quopri.decodestring, 'base64': base64.decodebytes}
MAIL_SERVERS = {'yandex.ru': ('pop.yandex.ru', 995),
                'mail.ru': ('pop.mail.ru', 995),
                'rambler.ru': ('pop.rambler.ru ', 995),
                'gmail.com': ('pop.gmail.com', 995)}
SUBJECT_TYPE_ENCODINGS = {'q': quopri.decodestring, 'Q': quopri.decodestring,
                          'b': base64.decodebytes, 'B': base64.decodebytes}

"""
regular expressions
"""
BOUNDARY_RE = re.compile(r'boundary="(.*?)"')
SUBJECT_RE = re.compile(r'Subject: =\?(.*?)\?(.*?)\?(.*?)\?=', re.IGNORECASE)
FILE_EXTENSION_RE = re.compile(r'/([^/]*?)$')
CONTENT_TYPE_RE = re.compile(r'Content-Type: (.*?);')
CHARSET_RE = re.compile(r'charset = "(.*?)"')
FROM_RE = re.compile(r'From:.*?([\d\w-]*@.*?\..{2,3})')
TO_RE = re.compile(r'To:.*?([\d\w-]*@.*?\..{2,3})')
CONTENT_TRANSFER_ENCODING_RE = re.compile(r'Content-Transfer-Encoding: (.*)\r')
CONTENT_RE = re.compile(r'\r\n\r\n(.*)', re.DOTALL)
FILENAME_RE = re.compile(r'filename="=\?(.*?)\?(.*?)\?(.*?)\?="')


class Client:
    def __init__(self):
        self.address, self.password, self.message_number = self.check_config()
        self.subject = ''

    def start(self):
        context = ssl.create_default_context()
        with socket(AF_INET, SOCK_STREAM) as tcp_socket:
            mail_server = MAIL_SERVERS[self.address.split('@')[1]]
            tcp_socket.connect(mail_server)
            with context.wrap_socket(tcp_socket, server_hostname=mail_server[0]) as stcp_socket:
                print(stcp_socket.recv(1024).decode())
                stcp_socket.send(f'USER {self.address}\r\n'.encode())  # почта
                print('Message after USER command:' + stcp_socket.recv(1024).decode())
                stcp_socket.send(f'PASS {self.password}\r\n'.encode())  # пароль
                print('Message after PASS command:' + stcp_socket.recv(1024).decode())
                stcp_socket.send(f'RETR {self.message_number}\r\n'.encode())
                print(stcp_socket.recv(1024).decode())
                message = ''
                while not message.endswith('\r\n.\r\n'):
                    message += stcp_socket.recv(1024).decode()
                self.decode_message(message)
                print('done')

    def decode_message(self, message):
        boundary = '--' + re.search(BOUNDARY_RE, message)[1]
        mime_re = re.compile(f'(Content-Type.*?){boundary}', re.DOTALL)
        bodies = re.findall(mime_re, message)
        if not self.subject:
            subject_dec = re.findall(SUBJECT_RE, message)[0]
            msg_from_dec = re.findall(FROM_RE, message)[0]
            print(msg_from_dec)
            msg_from = 'From: ' + re.findall(FROM_RE, message)[0]
            msg_to = 'To: ' + re.findall(TO_RE, message)[0]
            self.subject = SUBJECT_TYPE_ENCODINGS[subject_dec[1]](subject_dec[2].encode()).decode(
                subject_dec[0])
            self.create_messge_info(msg_from, msg_to)

        bodies.pop(0)
        for body in bodies:
            content_type = re.findall(CONTENT_TYPE_RE, body)[0]
            charset = re.findall(CHARSET_RE, body)
            content_transfer_encoding = re.findall(CONTENT_TRANSFER_ENCODING_RE, body)
            content = re.findall(CONTENT_RE, body)[0].encode()
            if content_type.startswith('multipart'):
                self.decode_message(body)
                continue
            filename = re.findall(FILENAME_RE, body)
            if filename:
                filename = SUBJECT_TYPE_ENCODINGS[filename[0][1]](filename[0][2].encode()).decode(
                    filename[0][0])
                print(filename)
            else:
                filename = self.subject
            if content_transfer_encoding:
                content = CONTENT_TRANSFER_ENCODINGS[content_transfer_encoding[0]](content)
            if charset:
                encoding = charset[0]
            else:
                encoding = 'utf-8'
            if content_type == 'text/plain':
                self.save_file(content, '.txt', encoding, filename)
            else:
                self.save_file(content, '.' + re.search(FILE_EXTENSION_RE, content_type).group(1),
                               encoding, filename)

    def save_file(self, content, extension, encoding, filename):
        if filename != self.subject:
            extension = ''
        with(open(filename + extension, 'w', encoding=encoding)) as f:
            pass
        with(open(filename + extension, 'wb')) as f:
            f.write(content)

    @staticmethod
    def check_config():
        try:
            with open('message\conf.txt', 'r') as f:
                address_from = f.readline()[:-1].split(' ')[1]
                password = f.readline()[:-1].split(' ')[1]
                message_number = f.readline()[:-1].split(' ')[1]
                return address_from, password, message_number
        except Exception:
            print('данные были введены не верно, прочитайте readme, и введите данные корректно')
            sys.exit()

    def create_messge_info(self, msg_from, msg_to):
        with open(f'{self.subject}_message_info.txt', 'w') as f:
            f.write(msg_from + '\n')
            f.write(msg_to + '\n')
            f.write('Subject: ' + self.subject + '\n')


if __name__ == '__main__':
    client = Client()
    client.start()
