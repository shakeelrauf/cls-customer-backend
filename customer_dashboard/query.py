import pyodbc
from django.conf import settings
import datetime
import logging
from customer_dashboard.custom_exception import NotFoundError, ConnectionError, ESCDataNotFetchingError

database = settings.DATABASES['esc']
logger = logging.getLogger(__name__)


# get cursor
def connect_to_server():
    try:
        conn = pyodbc.connect('DRIVER={'+database['OPTIONS']['driver']+'};SERVER='+database['HOST']+';DATABASE='+database['NAME']+';UID='+database['USER']+';PWD='+ database['PASSWORD'])
    except Exception as e:
        print('Exception :', e)
    else:
        return conn


# get data for company details API
def get_company_details(cus_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            data_dict = {}
            cust_query = f"""SELECT CustNo, LastName FROM Customer WHERE CustNo='{cus_no}'"""
            cust_res = cursor.execute(cust_query).fetchone()
            if cust_res:
                data_dict['cus_no'] = cust_res[0]
                data_dict['last_name'] = cust_res[1]
                query = f"""SELECT LocName, Add1, LocNo,CustNo FROM Location WHERE CustNo='{cus_no}'"""
                res = cursor.execute(query)
                if res:
                    ret_data = res.fetchall()
                    con.close()
                    data = []
                    for d in ret_data:
                        data.append({
                            'location': d[0],
                            'address': d[1],
                            'location_no': d[2],
                            'customer_no': d[3]
                        })
                    data_dict['data'] = data
                    return data_dict
            else:
                raise NotFoundError
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError

#update data for company API

def update_company_details(custNo,LocNo,data):
    location = data['location']
    address = data['address']
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            data_dict = {}
            update_loc_query = f"""UPDATE Location SET LocName='{location}', Add1='{address}' WHERE  CustNo='{custNo}' AND LocNo='{LocNo}'"""
            update_loc_res = cursor.execute(update_loc_query)
            cursor.commit()
            loc_query = f"""SELECT LocName,Add1 from Location WHERE CustNo='{custNo}' AND LocNo='{LocNo}'"""
            loc_res = cursor.execute(loc_query).fetchone()
            con.close()
            return loc_res
        except Exception as e:
            logger.error('%s', e)
            raise False
    else:
        raise ConnectionError

# get data for accounting API
import pdb
def get_accounting(cus_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            # fetch data from Location table
            location_query = f"""SELECT LocNo, LocName, Add1 FROM Location WHERE CustNo='{cus_no}'"""
            location_data = cursor.execute(location_query).fetchall()
            # fetch data from Customer table
            customer_query = f"""SELECT CustNo, LastName, Add1, Terms FROM Customer WHERE CustNo='{cus_no}'"""
            customer_data = cursor.execute(customer_query).fetchone()
            # dict for return data
            data_dict = {}
            # list for location and address list
            data = []
            # information of cus_no, last_name, terms, address
            if customer_data:
                for index, key in enumerate(('cus_no', 'last_name', 'address', 'terms')):
                    data_dict[key] = customer_data[index]
                # create list of address and locations
                if location_data:
                    for d in location_data:
                        # information of total unpaid amount
                        
                        #invoice_query = f"""SELECT SUM(CAST((Sales.AmtCharge+Sales.AmtCash+Sales.AmtCheck+Sales.AmtCreditC-Sales.AmtChng) AS DECIMAL(12,2))) FROM Sales  LEFT JOIN Receivab ON Sales.CustNo = Receivab.CustNo and Sales.Invoice = Receivab.Invoice WHERE Sales.CustNo='{cus_no}'
                            #                AND Sales.LocNo='{d[0]}' AND Receivab.PaidOff IS NULL"""
                        invoice_query = f"""SELECT SUM(CAST((InvAmt - Paid) AS DECIMAL(12,2)))  FROM Receivab WHERE LocNo='{d[0]}' AND CustNo='{cus_no}'"""
                        #invoice_query = f"""SELECT SUM([Invoice Total]) FROM dbo.ViewListInvoices WHERE Customer='{cus_no}' 
                                          #  AND Location='{d[0]}' AND [Paid Off Date] IS NULL"""
                        amount = cursor.execute(invoice_query).fetchone()[0]
                        if amount:
                            data.append({
                                'loc_no': d[0],
                                'location': d[1],
                                'address': d[2],
                                'amount': amount if amount is not None else 0
                            })
                total_amount = 0
                # calculate total unpaid amount

                for amt in data:
                    total_amount += amt['amount']
                data_dict['total_amount'] = total_amount
                #dues_query = f"""SELECT
                  #      SUM(CASE WHEN DATEDIFF(day,[Invoice Date], GETDATE())<=30 THEN [Invoice Total] ELSE 0 END),
                   #     SUM(CASE WHEN DATEDIFF(day,[Invoice Date], GETDATE())>30 AND DATEDIFF(day,[Invoice Date], GETDATE())<=60 THEN [Invoice Total] ELSE 0 END),
                    #    SUM(CASE WHEN DATEDIFF(day,[Invoice Date], GETDATE())>60 THEN [Invoice Total] ELSE 0 END)
                     #   FROM ViewListInvoices
                      #  WHERE Customer='{cus_no}' AND [Paid Off Date] IS NULL"""
               
                dues_query = f"""SELECT
                        SUM(CASE WHEN DATEDIFF(day,CONVERT(datetime,(Period+'01')), GETDATE())<=30 THEN CAST((InvAmt - Period) AS DECIMAL(12,2)) ELSE 0 END),
                        SUM(CASE WHEN DATEDIFF(day,CONVERT(datetime,(Period+'01')), GETDATE())>30 AND DATEDIFF(day,CONVERT(datetime,(Period+'01')), GETDATE())<=60 THEN CAST((InvAmt - Period) AS DECIMAL(12,2)) ELSE 0 END),
                        SUM(CASE WHEN DATEDIFF(day,CONVERT(datetime,(Period+'01')), GETDATE())>60 THEN CAST((InvAmt -  Period) AS DECIMAL(12,2)) ELSE 0 END)
                        FROM Receivab 
                        WHERE CustNo='{cus_no}' """    
                dues = cursor.execute(dues_query).fetchone()
                data_dict['over_30'] = dues[0]
                data_dict['over_60'] = dues[1]
                data_dict['over_90'] = dues[2]
                data_dict['data'] = data
                con.close()
                return data_dict
            else:
                raise NotFoundError
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get list of invoice (accounting tab)
def get_invoice_list(cus_no, loc_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            #query = f"""SELECT Sales.Invoice, Sales.InvDate, CAST(Sales.InvAmount AS DECIMAL(12,2)), CAST((Sales.AmtCharge+Sales.AmtCash+Sales.AmtCheck+Sales.AmtCreditC-Sales.AmtChng - Sales.InvAmount) AS DECIMAL(12,2)), CAST((Sales.AmtCharge+Sales.AmtCash+Sales.AmtCheck+Sales.AmtCreditC-Sales.AmtChng) AS DECIMAL(12,2)) FROM Sales 
             #           LEFT JOIN Receivab ON Sales.CustNo = Receivab.CustNo and Sales.Invoice = Receivab.Invoice
              #          WHERE Sales.CustNo='{cus_no}' AND Sales.LocNo='{loc_no}' AND Receivab.PaidOff IS NULL AND 
               #         CAST((Sales.AmtCharge+Sales.AmtCash+Sales.AmtCheck+Sales.AmtCreditC-Sales.AmtChng) AS DECIMAL(12,2)) > 0"""
            query = f""" SELECT Invoice, InvDate, InvAmt, Paid, InvAmt-Paid FROM Receivab WHERE LocNo='{loc_no}' AND CustNo='{cus_no}' AND (InvAmt-Paid) != '0' """
            invoice_list = cursor.execute(query).fetchall()
            data = []
            for invoice in invoice_list:
                data.append({
                    'invoice': invoice[0],
                    'do_date': invoice[1] + datetime.timedelta(days=30),
                    'invoice_date': invoice[1],
                    'sub_total': invoice[2],
                    'tax': invoice[3],
                    'total': invoice[4]
                })
            con.close()
            return data
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get invoice list for mailing query
def get_invoice_for_query(cus_no, loc_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            query = f"""SELECT Sales.Invoice FROM Sales
                        LEFT JOIN Receivab ON Sales.CustNo = Receivab.CustNo and Sales.Invoice = Receivab.Invoice
                        WHERE Sales.CustNo='{cus_no}' AND Sales.LocNo='{loc_no}' 
                        AND Receivab.PaidOff IS NULL AND CAST((Sales.AmtCharge+Sales.AmtCash+Sales.AmtCheck+Sales.AmtCreditC-Sales.AmtChng) AS DECIMAL(12,2)) > 0"""
            invoice_list = cursor.execute(query).fetchall()
            data = []
            for invoice in invoice_list:
                data.append(invoice[0])
            con.close()
            return data
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get invoice detail (for payment)
def get_invoice(cus_no, loc_no, invoice):
    con = connect_to_server()
    if con:
        try:
            data_dict = {}
            cursor = con.cursor()
            customer_query = f"""SELECT CustNo, LastName FROM Customer WHERE CustNo='{cus_no}'"""
            customer_data = cursor.execute(customer_query).fetchone()
            for index, cus in enumerate(('cus_no', 'name')):
                data_dict[cus] = customer_data[index]
            location_query = f"""SELECT LocName, Add1 FROM Location WHERE CustNo='{cus_no}' AND LocNo='{loc_no}'"""
            location_data = cursor.execute(location_query).fetchone()
            for i, loc in enumerate(('loc_name', 'address')):
                data_dict[loc] = location_data[i]
            invoice_query = f"""SELECT Invoice, InvDate, CAST((InvAmt  - Paid) AS DECIMAL(12,2)) FROM Receivab WHERE 
                                Invoice='{invoice}'"""
            invoice_data = cursor.execute(invoice_query).fetchone()
            for j, inv in enumerate(('invoice', 'invoice_date', 'total')):
                data_dict[inv] = invoice_data[j]
            sales_query = f"""SELECT [Desc], Quan, Price, Amount, Tax1, Tax2, Tax3, Tax4 FROM SalesLed WHERE 
                              Invoice='{invoice}' AND NOT Prod = 'NOTES' AND NOT Prod = 'Break'"""
            sales_data = cursor.execute(sales_query).fetchall()
            data = []
            tax = 0
            sub_total = 0
            for inv_data in sales_data:
                data.append({
                    'desc': inv_data[0],
                    'quantity': inv_data[1],
                    'price': inv_data[2],
                    'amount': inv_data[3],
                })
                tax += sum(inv_data[4:])
            for d in data:
                sub_total += d['amount']
            data_dict['sub_total'] = sub_total
            data_dict['GST'] = "%.2f" % tax
            data_dict['data'] = data
            con.close()
            return data_dict
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# quotation API
def get_quotations(cus_no, status):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            data_dict = {}
            # fetch data for Customer table
            customer_query = f"""SELECT CustNo, LastName, Add1, Terms FROM Customer WHERE CustNo='{cus_no}'"""
            customer_data = cursor.execute(customer_query).fetchone()
            if customer_data:
                for i, cus in enumerate(('cus_no', 'last_name', 'address')):
                    data_dict[cus] = customer_data[i]
                # fetch data from Location table
                data = []
                location_query = f"""SELECT LocNo, LocName, Add1 FROM Location WHERE CustNo='{cus_no}'"""
                location_data = cursor.execute(location_query).fetchall()
                for loc in location_data:
                    # get open quotes
                    quote_query = f"""SELECT COUNT(*) FROM dbo.ViewListQuotes WHERE [Quote Status]='{status.title()}' AND
                                      Customer='{cus_no}' AND Location='{loc[0]}'"""
                    open_quotes = cursor.execute(quote_query).fetchone()[0]
                    if open_quotes > 0:
                        data.append({
                            'loc_no': loc[0],
                            'location': loc[1],
                            'address': loc[2],
                            'quotes': open_quotes
                        })
                data_dict['data'] = data
                return data_dict
            else:
                raise NotFoundError
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get quotes list (quotation tab)
def get_quotes_list(cus_no, loc_no, status):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            query = f"""SELECT Quote, [Quote Date], [Sales Person Name], Amount FROM dbo.ViewListQuotes 
                        WHERE Customer='{cus_no}' AND Location='{loc_no}' AND [Quote Status] = '{status}' AND
                        [Invoice Total] > 0"""
            quotes_list = cursor.execute(query).fetchall()
            data = []
            for quote in quotes_list:
                data.append({
                    'quote': quote[0],
                    'quote_date': quote[1],
                    'sales_person': quote[2],
                    'amount': quote[3]
                })
            con.close()
            return data
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get quotation detail (for quotation)
def get_quotes(cus_no, loc_no, quote):
    con = connect_to_server()
    if con:
        try:
            data_dict = {}
            cursor = con.cursor()
            customer_query = f"""SELECT CustNo, LastName FROM Customer WHERE CustNo='{cus_no}'"""
            customer_data = cursor.execute(customer_query).fetchone()
            for index, cus in enumerate(('cus_no', 'name')):
                data_dict[cus] = customer_data[index]
            location_query = f"""SELECT LocName, Add1 FROM Location WHERE CustNo='{cus_no}' AND LocNo='{loc_no}'"""
            location_data = cursor.execute(location_query).fetchone()
            for i, loc in enumerate(('loc_name', 'address')):
                data_dict[loc] = location_data[i]
            sales_query = f"""SELECT Invoice, [Desc], Quan, Price, Amount FROM SalesLed WHERE Invoice='{quote}' 
                              AND NOT Prod='NOTES' AND NOT Prod = 'Break'"""
            sales_data = cursor.execute(sales_query).fetchall()
            sales = []
            detail = {}
            for d in sales_data:
                for j, qte in enumerate(('invoice', 'desc', 'quantity', 'price', 'amount')):
                    detail[qte] = d[j]
                sales.append(detail)
                detail = {}
            data_dict['sales_data'] = sales
            quote_query = f"""SELECT Quote, Customer, Location, [Quote Date], [Sales Person Name], [Purchase Order], Amount,
                              [Quote Status], Tax, [Invoice Total] FROM dbo.ViewListQuotes WHERE Quote='{quote}'"""
            quote_data = cursor.execute(quote_query).fetchone()
            cols = ('quote', 'customer', 'location', 'quote_date', 'sales_person', 'purchase_order', 'amount',
                    'quote_status', 'tax', 'invoice_total')
            for k, data in enumerate(cols):
                data_dict[data] = quote_data[k]
            data_dict['pay_amount'] = float(data_dict['invoice_total']) / 4
            con.close()
            return data_dict
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get data for service request API
def get_service_request(cus_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            data_dict = {}
            data_dict['last_name'] = cursor.execute(f"SELECT LastName FROM Customer WHERE CustNo='{cus_no}'").fetchone()[0]
            data_dict['cus_no'] = cus_no
            query = f"""SELECT LocNo, LocName, Add1 FROM Location WHERE CustNo='{cus_no}'"""
            res = cursor.execute(query)
            if res:
                ret_data = res.fetchall()
                data = []
                for d in ret_data:
                    data.append({
                        'loc_no': d[0],
                        'location': d[1],
                        'address': d[2]
                    })
                data_dict['data'] = data
                con.close()
                return data_dict
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get last name of customer (for system number page)
def get_last_name(cus_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            last_name = cursor.execute(f"SELECT LastName FROM Customer WHERE CustNo='{cus_no}'").fetchone()
            con.close()
            if last_name:
                return last_name[0]
            else:
                raise NotFoundError
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get list of invoice and its amount on the basis of location and customer number
def get_all_invoice_of_location(cus_no, loc_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            query = f"""SELECT Invoice, 
            CAST((InvAmt - Paid) AS DECIMAL(12,2))
                         FROM  Receivab
                         WHERE CustNo='{cus_no}' 
                         AND LocNo='{loc_no}' AND  CAST((InvAmt - Paid) AS DECIMAL(12,2)) > 0"""
            invoice_list = cursor.execute(query).fetchall()
            data = []
            for invoice in invoice_list:
                data.append({
                    'invoice': invoice[0],
                    'amount': invoice[1]
                })
            con.close()
            return data
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# get list of all invoice
def get_all_invoice(cus_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            query = f"""SELECT Invoice, 
                    CAST((InvAmt - Paid) AS DECIMAL(12,2))
                    FROM Receivab WHERE CustNo='{cus_no}' AND
                    CAST((InvAmt - Paid) AS DECIMAL(12,2)) > 0"""
            invoice_list = cursor.execute(query).fetchall()
            data = []
            for invoice in invoice_list:
                data.append({
                    'invoice': invoice[0],
                    'amount': invoice[1]
                })
            con.close()
            return data
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# function for getting location name
def get_location_name(cus_no, loc_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            query = f"""SELECT Add1 FROM Location WHERE CustNo='{cus_no}' AND LocNo='{loc_no}'"""
            res = cursor.execute(query)
            if res:
                ret_data = res.fetchall()
                con.close()
                return ret_data
            else:
                raise NotFoundError
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError


# all invoice list with location and address
def get_invoice_list_with_address(cus_no):
    con = connect_to_server()
    if con:
        try:
            cursor = con.cursor()
            query = f"""SELECT Customer.LastName, Location.Add1, dbo.ViewListInvoices.Invoice, 
                        dbo.ViewListInvoices.[Invoice Total] FROM dbo.ViewListInvoices 
                        INNER JOIN Location ON Location.CustNo = dbo.ViewListInvoices.Customer AND 
                        dbo.ViewListInvoices.Location = Location.LocNo 
                        INNER JOIN Customer ON Customer.CustNo=dbo.ViewListInvoices.Customer 
                        WHERE dbo.ViewListInvoices.Customer='{cus_no}' AND dbo.ViewListInvoices.[Paid Off Date] IS NULL 
                        AND dbo.ViewListInvoices.[Invoice Total] > 0"""
            invoice_list = cursor.execute(query).fetchall()
            data = []
            for inv in invoice_list:
                if len(data) == 0:
                    data.append({
                        'location': inv[0],
                        'address': inv[1],
                        'list_of_invoice': [{
                            'invoice': inv[2],
                            'amount': inv[3]
                        }]
                    })
                else:
                    if inv[1] not in [i['address'] for i in data]:
                        data.append({
                            'location': inv[0],
                            'address': inv[1],
                            'list_of_invoice': [{
                                'invoice': inv[2],
                                'amount': inv[3]
                            }]
                        })
                    else:
                        for j in data:
                            if j['address'] == inv[1]:
                                j['list_of_invoice'].append({
                                    'invoice': inv[2],
                                    'amount': inv[3]
                                })
            con.close()
            for d in data:
                d['amount'] = sum([inv['amount'] for inv in d['list_of_invoice']])
            return data
        except Exception as e:
            logger.error('%s', e)
            raise ESCDataNotFetchingError
    else:
        raise ConnectionError
