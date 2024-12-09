from sms_ir import SmsIr



class MessageService:
    def __init__(self):
        self.sender = SmsIr('hSXifEBzb4cPgyZYMhfFaUaFtusHV6N5r5NcaEuL8eOh7zYq', 3000786512)

    def send_message(self, message, number):
        self.sender.send_sms(number,  message)