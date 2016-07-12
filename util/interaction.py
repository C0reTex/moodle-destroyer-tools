import math
import getpass
import sys
import shutil


def input_choices_from_list(choices, text):
    """Lets the user choose from a list

    Args:
        choices (list): the list the choose from
        text (str): the text to display for user input
    Returns:
        a list of indices chosen by the user
    """

    digits = str(math.ceil(math.log10(len(choices))))
    format_str = '{:' + digits + 'd} {}'
    for n, c in enumerate(choices, 0):
        print(format_str.format(n, c))
    chosen = [int(c) for c in input(text).split()]
    return chosen


def get_user_pref(text, option):
    pref = input(text.format(option))

    if pref == '':
        return option
    else:
        return pref


def input_password():
    password_text = """
      Please insert your Moodle password.
      It will not be saved, it is required to get a token.
      Attention: keep your token safe until MDL-53400 is resolved.
      Until then it CANNOT be reset.
    Password: """
    return getpass.getpass(prompt=password_text)


def input_moodle_url(url=''):
    url_text = """
    The location of you moodle like "moodle.hostname.org/moodle"
    Moodle [{}]: """
    return get_user_pref(url_text, url)


def input_user_name(user_name=''):
    user_text = '    Your Moodle username [{}]: '
    return get_user_pref(user_text, user_name)


def print_progress(iteration, total, prefix='', suffix='', decimals=2, bar_length=100):
    col_width = shutil.get_terminal_size().columns
    filled_length = int(round(bar_length * iteration / float(total)))
    percents = round(100.00 * (iteration / float(total)), decimals)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    output_line = '\r{} |{}| {}% {}'.format(prefix, bar, percents, suffix)
    if len(output_line) > col_width :
        diff = len(output_line) - col_width
        suffix = suffix[diff:]
        output_line = '\r{} |{}| {}% {}'.format(prefix, bar, percents, suffix)
    else:
        diff = col_width - len(output_line)
        output_line += ' '*diff

    sys.stdout.write(output_line),
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')
        sys.stdout.flush()
