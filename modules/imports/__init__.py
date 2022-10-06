from beancount.query import query, query_compile
from beancount.query.query_env import TargetsEnvironment
from ..accounts import *
import re
import csv
from beancount.parser.printer import EntryPrinter, format_entry
from beancount.core import data
import sys
import codecs


def my_print_entries(entries, dcontext=None, render_weights=False, file=None, prefix=None):
    """A convenience function that prints a list of entries to a file.

    Args:
      entries: A list of directives.
      dcontext: An instance of DisplayContext used to format the numbers.
      render_weights: A boolean, true to render the weights for debugging.
      file: An optional file object to write the entries to.
    """
    assert isinstance(entries, list), "Entries is not a list: {}".format(entries)
    output_d = file or (codecs.getwriter("utf-8")(sys.stdout.buffer)
                      if hasattr(sys.stdout, 'buffer') else
                      sys.stdout)
    yuebao = open('yuebao.bean', 'w')
    water = open('water.bean', 'w')

    previous_type = type(entries[0]) if entries else None
    eprinter = EntryPrinter(dcontext, render_weights)
    for entry in entries:
        # Insert a newline between transactions and between blocks of directives
        # of the same type.

        if '后勤服务有限公司' in entry.payee and entry.narration == '直饮水':
            output = water
        elif entry.payee == '余额宝' and entry.narration == '收益':
            output = yuebao
        else:
            output = output_d

        entry_type = type(entry)
        if (entry_type in (data.Transaction, data.Commodity) or
            entry_type is not previous_type):
            output.write('\n')
            previous_type = entry_type

        string = format_entry(entry, prefix=prefix)
        output.write(string)

    yuebao.close()
    water.close()

def create_simple_posting_with_meta(entry, account, number, currency, meta):
    """Create a simple posting on the entry, with just a number and currency (no cost).

    Args:
      entry: The entry instance to add the posting to.
      account: A string, the account to use on the posting.
      number: A Decimal number or string to use in the posting's Amount.
      currency: A string, the currency for the Amount.
    Returns:
      An instance of Posting, and as a side-effect the entry has had its list of
      postings modified with the new Posting instance.
    """
    if isinstance(account, str):
        pass
    if number is None:
        units = None
    else:
        if not isinstance(number, data.Decimal):
            number = data.D(number)
        units = data.Amount(number, currency)
    posting = data.Posting(account, units, None, None, None, meta)
    if entry is not None:
        entry.postings.append(posting)
    return posting


def replace_flag(entry, flag):
    return entry._replace(flag='!')


def get_account_by_guess(from_user, description, time=None):
    if description != '':
        for key, value in descriptions.items():
            if description_res[key].findall(description):
                if callable(value):
                    return value(from_user, description, time)
                else:
                    return value
                break
    for key, value in anothers.items():
        if another_res[key].findall(from_user):
            if callable(value):
                return value(from_user, description, time)
            else:
                return value
            break
    return "Expenses:Unknown"


def get_income_account_by_guess(from_user, description, time=None):
    for key, value in incomes.items():
        if income_res[key].findall(description):
            return value
        if income_res[key].findall(from_user):
            return value
    return "Income:Unknown"


def get_account_by_name(name, time=None):
    if accounts.get(name, '') == '':
        return "Unknown:" + name
    else:
        return accounts.get(name)


def map_pn(from_user, description, time=None):
    for key, value in pn.items():
        if pn_res[key].findall(from_user):
            return (re.sub(value['p'][0], value['p'][1], from_user),
                    re.sub(value['n'][0], value['n'][1], description))
    return (from_user, description)


def map_tag(from_user, description, shop_trade_no, time=None):
    for key, value in tag.items():
        if tag_res[key].findall(from_user):
            return [value]
        elif tag_res[key].findall(description):
            return [value]
        elif tag_res[key].findall(shop_trade_no):
            return [value]
    return []


def map_link(from_user, description, shop_trade_no, time=None):
    for key, value in link.items():
        if link_res[key].findall(from_user):
            return [value]
        elif link_res[key].findall(description):
            return [value]
        elif link_res[key].findall(shop_trade_no):
            return [value]
    return []


def map_meta(from_user, description, time=None):
    for key, value in meta.items():
        if meta_res[key].findall(from_user):
            return value
        elif meta_res[key].findall(description):
            return value
    return None


class DictReaderStrip(csv.DictReader):
    @property
    def fieldnames(self):
        if self._fieldnames is None:
            # Initialize self._fieldnames
            # Note: DictReader is an old-style class, so can't use super()
            csv.DictReader.fieldnames.fget(self)
            if self._fieldnames is not None:
                self._fieldnames = [name.strip() for name in self._fieldnames]
        return self._fieldnames

    def __next__(self):
        if self.line_num == 0:
            # Used only for its side effect.
            self.fieldnames
        row = next(self.reader)
        self.line_num = self.reader.line_num

        # unlike the basic reader, we prefer not to return blanks,
        # because we will typically wind up with a dict full of None
        # values
        while row == []:
            row = next(self.reader)
        row = [element.strip() for element in row]
        d = dict(zip(self.fieldnames, row))
        lf = len(self.fieldnames)
        lr = len(row)
        if lf < lr:
            d[self.restkey] = row[lf:].strip()
        elif lf > lr:
            for key in self.fieldnames[lr:]:
                d[key] = self.restval.strip()
        return d


class Metas(query_compile.EvalFunction):
    __intypes__ = []

    def __init__(self, operands):
        super().__init__(operands, object)

    def __call__(self, context):
        args = self.eval_args(context)
        meta = context.entry.meta
        return meta


TargetsEnvironment.functions['metas'] = Metas
