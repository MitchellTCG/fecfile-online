from django.shortcuts import render
import datetime
import json
import logging
import os
from decimal import Decimal

import requests
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from fecfiler.core.views import (NoOPError, check_null_value, check_report_id,
                                 date_format, delete_entities, get_entities,
                                 post_entities, put_entities, remove_entities,
                                 undo_delete_entities)
from fecfiler.sched_A.views import get_next_transaction_id
from fecfiler.sched_D.views import do_transaction


# Create your views here.
logger = logging.getLogger(__name__)

MANDATORY_FIELDS_SCHED_C2 = ['cmte_id', 'report_id', 'transaction_id']
MANDATORY_FIELDS_SCHED_C1 = ['cmte_id', 'report_id',
                             'line_number', 'transaction_type', 'transaction_id']
MANDATORY_FIELDS_SCHED_C = ['cmte_id', 'report_id',
                            'line_number', 'transaction_type', 'transaction_id']


def check_transaction_id(transaction_id):
    if not (transaction_id[0:2] == "SC"):
        raise Exception(
            'The Transaction ID: {} is not in the specified format.' +
            'Transaction IDs start with SD characters'.format(transaction_id))
    return transaction_id


def check_mandatory_fields_SC(data):
    """
    validate mandatory fields for sched_c item
    """
    try:
        errors = []
        for field in MANDATORY_FIELDS_SCHED_C:
            if not(field in data and check_null_value(data.get(field))):
                errors.append(field)
        if errors:
            raise Exception(
                'The following mandatory fields are required in order to save data to schedA table: {}'.format(','.join(errors)))
    except:
        raise


def schedC_sql_dict(data):
    """
    filter out valid fileds for sched_c
    """
    valid_fields = [
            'line_number',
            'transaction_type',
            'transaction_type_identifier',
            'entity_id',
            'election_code',
            'election_other_description',
            'loan_amount_original',
            'loan_payment_to_date',
            'loan_balance',
            'loan_incurred_date',
            'loan_due_date',
            'loan_intrest_rate',
            'is_loan_secured',
            'is_personal_funds',
            'lender_cmte_id',
            'lender_cand_id',
            'lender_cand_last_name',
            'lender_cand_first_name',
            'lender_cand_middle_name',
            'lender_cand_prefix',
            'lender_cand_suffix',
            'lender_cand_office',
            'lender_cand_state',
            'lender_cand_district',
            'memo_code',
            'memo_text',
    ]
    try:
        return {k: v for k, v in data.items() if k in valid_fields}
    except:
        raise Exception('invalid request data.')


def put_schedC(data):
    """
    update sched_c item
    here we are assuming entity_id are always referencing something already in our DB
    """
    try:
        check_mandatory_fields_SC(data)
        #check_transaction_id(data.get('transaction_id'))
        try:
            put_sql_schedC(data)
        except Exception as e:
            raise Exception(
                'The put_sql_schedC function is throwing an error: ' + str(e))
        return data
    except:
        raise


def put_sql_schedC(data):
    """
    uopdate a schedule_c item
    """
    _sql = """UPDATE public.sched_c
              SET transaction_type = %s,
                  transaction_type_identifier = %s,
                  entity_id = %s,
                  election_code = %s,
                  election_other_description = %s,
                  loan_amount_original = %s,
                  loan_payment_to_date = %s,
                  loan_balance = %s,
                  loan_incurred_date = %s,
                  loan_due_date = %s,
                  loan_intrest_rate = %s,
                  is_loan_secured = %s,
                  is_personal_funds = %s,
                  lender_cmte_id = %s,
                  lender_cand_id = %s,
                  lender_cand_last_name = %s,
                  lender_cand_first_name = %s,
                  lender_cand_middle_name = %s,
                  lender_cand_prefix = %s,
                  lender_cand_suffix = %s,
                  lender_cand_office = %s,
                  lender_cand_state = %s,
                  lender_cand_district = %s,
                  memo_code = %s,
                  memo_text = %s,
                  last_update_date = %s
              WHERE transaction_id = %s AND report_id = %s AND cmte_id = %s 
              AND delete_ind is distinct from 'Y';
        """
    _v = (
            data.get('transaction_type', ''),
            data.get('transaction_type_identifier', ''),
            data.get('entity_id', ''),
            data.get('election_code', ''),
            data.get('election_other_description', ''),
            data.get('loan_amount_original', None),
            data.get('loan_payment_to_date', None),
            data.get('loan_balance', None),
            data.get('loan_incurred_date', None),
            data.get('loan_due_date', None),
            data.get('loan_intrest_rate', ''),
            data.get('is_loan_secured', ''),
            data.get('is_personal_funds', ''),
            data.get('lender_cmte_id', ''),
            data.get('lender_cand_id', ''),
            data.get('lender_cand_last_name', ''),
            data.get('lender_cand_first_name', ''),
            data.get('lender_cand_middle_name', ''),
            data.get('lender_cand_prefix', ''),
            data.get('lender_cand_suffix', ''),
            data.get('lender_cand_office', ''),
            data.get('lender_cand_state', ''),
            data.get('lender_cand_district', None),
            data.get('memo_code', ''),
            data.get('memo_text', ''),
            datetime.datetime.now(),
            data.get('transaction_id'),
            data.get('report_id'),
            data.get('cmte_id'),
          )
    do_transaction(_sql, _v)


def validate_sc_data(data):
    """
    validate sc json data
    """
    check_mandatory_fields_SC(data)


def post_schedC(data):
    """
    function for handling POST request for sc, need to:
    1. generatye new transaction_id
    2. validate data
    3. save data to db
    """
    try:
        # check_mandatory_fields_SA(datum, MANDATORY_FIELDS_SCHED_A)
        data['transaction_id'] = get_next_transaction_id('SC')
        print(data)
        validate_sc_data(data)
        try:
            post_sql_schedC(data)
        except Exception as e:
            raise Exception(
                'The post_sql_schedC function is throwing an error: ' + str(e))
        return data
    except:
        raise


def post_sql_schedC(data):
    try:
        _sql = """
        INSERT INTO public.sched_c (
            cmte_id,
            report_id,
            line_number,
            transaction_type,
            transaction_type_identifier,
            transaction_id,
            entity_id,
            election_code,
            election_other_description,
            loan_amount_original,
            loan_payment_to_date,
            loan_balance,
            loan_incurred_date,
            loan_due_date,
            loan_intrest_rate,
            is_loan_secured,
            is_personal_funds,
            lender_cmte_id,
            lender_cand_id,
            lender_cand_last_name,
            lender_cand_first_name,
            lender_cand_middle_name,
            lender_cand_prefix,
            lender_cand_suffix,
            lender_cand_office,
            lender_cand_state,
            lender_cand_district,
            memo_code,
            memo_text,
            create_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
        """
        _v = (
            data.get('cmte_id'),
            data.get('report_id'),
            data.get('line_number'),
            data.get('transaction_type'),
            data.get('transaction_type_identifier', ''),
            data.get('transaction_id'),
            data.get('entity_id', ''),
            data.get('election_code', ''),
            data.get('election_other_description', ''),
            data.get('loan_amount_original', None),
            data.get('loan_payment_to_date', None),
            data.get('loan_balance', None),
            data.get('loan_incurred_date', None),
            data.get('loan_due_date', None),
            data.get('loan_intrest_rate', ''),
            data.get('is_loan_secured', ''),
            data.get('is_personal_funds', ''),
            data.get('lender_cmte_id', ''),
            data.get('lender_cand_id', ''),
            data.get('lender_cand_last_name', ''),
            data.get('lender_cand_first_name', ''),
            data.get('lender_cand_middle_name', ''),
            data.get('lender_cand_prefix', ''),
            data.get('lender_cand_suffix', ''),
            data.get('lender_cand_office', ''),
            data.get('lender_cand_state', ''),
            data.get('lender_cand_district', None),
            data.get('memo_code', ''),
            data.get('memo_text', ''),
            datetime.datetime.now(),
        )
        with connection.cursor() as cursor:
            # Insert data into schedD table
            cursor.execute(_sql, _v)
    except Exception:
        raise


def get_schedC(data):
    """
    load sched_c data based on cmte_id, report_id and transaction_id
    """
    try:
        cmte_id = data.get('cmte_id')
        report_id = data.get('report_id')
        if 'transaction_id' in data:
            transaction_id = check_transaction_id(data.get('transaction_id'))
            forms_obj = get_list_schedC(report_id, cmte_id, transaction_id)
        else:
            forms_obj = get_list_all_schedC(report_id, cmte_id)
        return forms_obj
    except:
        raise


def get_list_all_schedC(report_id, cmte_id):

    try:
        with connection.cursor() as cursor:
            # GET single row from schedA table
            _sql = """SELECT json_agg(t) FROM ( SELECT
            cmte_id,
            report_id,
            line_number,
            transaction_type,
            transaction_type_identifier,
            transaction_id,
            entity_id,
            election_code,
            election_other_description,
            loan_amount_original,
            loan_payment_to_date,
            loan_balance,
            loan_incurred_date,
            loan_due_date,
            loan_intrest_rate,
            is_loan_secured,
            is_personal_funds,
            lender_cmte_id,
            lender_cand_id,
            lender_cand_last_name,
            lender_cand_first_name,
            lender_cand_middle_name,
            lender_cand_prefix,
            lender_cand_suffix,
            lender_cand_office,
            lender_cand_state,
            lender_cand_district,
            memo_code,
            memo_text,
            last_update_date
            FROM public.sched_c
            WHERE report_id = %s AND cmte_id = %s
            AND delete_ind is distinct from 'Y') t
            """
            cursor.execute(_sql, (report_id, cmte_id))
            schedC2_list = cursor.fetchone()[0]
            if schedC2_list is None:
                raise NoOPError('No sched_c1 transaction found for report_id {} and cmte_id: {}'.format(
                    report_id, cmte_id))
            merged_list = []
            for dictC2 in schedC2_list:
                merged_list.append(dictC2)
        return merged_list
    except Exception:
        raise


def get_list_schedC(report_id, cmte_id, transaction_id):
    try:
        with connection.cursor() as cursor:
            # GET single row from schedA table
            _sql = """SELECT json_agg(t) FROM ( SELECT
            cmte_id,
            report_id,
            line_number,
            transaction_type,
            transaction_type_identifier,
            transaction_id,
            entity_id,
            election_code,
            election_other_description,
            loan_amount_original,
            loan_payment_to_date,
            loan_balance,
            loan_incurred_date,
            loan_due_date,
            loan_intrest_rate,
            is_loan_secured,
            is_personal_funds,
            lender_cmte_id,
            lender_cand_id,
            lender_cand_last_name,
            lender_cand_first_name,
            lender_cand_middle_name,
            lender_cand_prefix,
            lender_cand_suffix,
            lender_cand_office,
            lender_cand_state,
            lender_cand_district,
            memo_code,
            memo_text,
            last_update_date
            FROM public.sched_c
            WHERE report_id = %s AND cmte_id = %s AND transaction_id = %s
            AND delete_ind is distinct from 'Y') t
            """
            cursor.execute(_sql, (report_id, cmte_id, transaction_id))
            schedC_list = cursor.fetchone()[0]
            if schedC_list is None:
                raise NoOPError('No sched_c transaction found for transaction_id {}'.format(
                    transaction_id))
            merged_list = []
            for dictC in schedC_list:
                merged_list.append(dictC)
        return merged_list
    except Exception:
        raise


def delete_schedC(data):
    """
    function for handling delete request for sc
    """
    try:
        # check_mandatory_fields_SC2(data)
        delete_sql_schedC(data.get('cmte_id'), data.get(
            'report_id'), data.get('transaction_id'))
    except Exception as e:
        raise


def delete_sql_schedC(cmte_id, report_id, transaction_id):
    """
    do delete sql transaction
    """
    _sql = """UPDATE public.sched_c
            SET delete_ind = 'Y' 
            WHERE transaction_id = %s AND report_id = %s AND cmte_id = %s
        """
    _v = (transaction_id, report_id, cmte_id)
    do_transaction(_sql, _v)


@api_view(['POST', 'GET', 'DELETE', 'PUT'])
def schedC(request):
    """
    sched_c1 api supporting POST, GET, DELETE, PUT
    """

    # create new sched_c1 transaction
    if request.method == 'POST':
        try:
            cmte_id = request.user.username
            if not('report_id' in request.data):
                raise Exception('Missing Input: Report_id is mandatory')
            # handling null,none value of report_id
            if not (check_null_value(request.data.get('report_id'))):
                report_id = "0"
            else:
                report_id = check_report_id(request.data.get('report_id'))
            # end of handling
            datum = schedC_sql_dict(request.data)
            datum['report_id'] = report_id
            datum['cmte_id'] = cmte_id
            if 'transaction_id' in request.data and check_null_value(
                    request.data.get('transaction_id')):
                datum['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
                data = put_schedC(datum)
            else:
                print(datum)
                data = post_schedC(datum)
            # Associating child transactions to parent and storing them to DB

            output = get_schedC(data)
            return JsonResponse(output[0], status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response("The schedC API - POST is throwing an exception: "
                            + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        try:
            data = {
                'cmte_id': request.user.username
            }
            if 'report_id' in request.data and check_null_value(request.data.get('report_id')):
                data['report_id'] = check_report_id(
                    request.data.get('report_id'))
            else:
                raise Exception('Missing Input: report_id is mandatory')
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                data['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
            datum = get_schedC(data)
            return JsonResponse(datum, status=status.HTTP_200_OK, safe=False)
        except NoOPError as e:
            logger.debug(e)
            forms_obj = []
            return JsonResponse(forms_obj, status=status.HTTP_204_NO_CONTENT, safe=False)
        except Exception as e:
            logger.debug(e)
            return Response("The schedC API - GET is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        try:
            data = {
                'cmte_id': request.user.username
            }
            if 'report_id' in request.data and check_null_value(request.data.get('report_id')):
                data['report_id'] = check_report_id(
                    request.data.get('report_id'))
            else:
                raise Exception('Missing Input: report_id is mandatory')
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                data['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
            else:
                raise Exception('Missing Input: transaction_id is mandatory')
            delete_schedC(data)
            return Response("The Transaction ID: {} has been successfully deleted".format(data.get('transaction_id')), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response("The schedC API - DELETE is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        try:
            datum = schedC_sql_dict(request.data)
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                datum['transaction_id'] = request.data.get('transaction_id')
            else:
                raise Exception('Missing Input: transaction_id is mandatory')

            if not('report_id' in request.data):
                raise Exception('Missing Input: Report_id is mandatory')
            # handling null,none value of report_id
            if not (check_null_value(request.data.get('report_id'))):
                report_id = "0"
            else:
                report_id = check_report_id(request.data.get('report_id'))
            # end of handling
            datum['report_id'] = report_id
            datum['cmte_id'] = request.user.username

            # if 'entity_id' in request.data and check_null_value(request.data.get('entity_id')):
            #     datum['entity_id'] = request.data.get('entity_id')
            # if request.data.get('transaction_type') in CHILD_SCHED_B_TYPES:
            #     data = put_schedB(datum)
            #     output = get_schedB(data)
            # else:
            data = put_schedC(datum)
            # output = get_schedA(data)
            return JsonResponse(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.debug(e)
            return Response("The schedC API - PUT is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    else:
        raise NotImplementedError


def schedC1_sql_dict(data):
    valid_fields = [
            'line_number',
            'transaction_type',
            'transaction_type_identifier',
            'lender_entity_id',
            'loan_amount',
            'loan_intrest_rate',
            'loan_incurred_date',
            'loan_due_date',
            'is_loan_restructured',
            'original_loan_date',
            'credit_amount_this_draw',
            'total_outstanding_balance',
            'other_parties_liable',
            'pledged_collateral_ind',
            'pledge_collateral_desc',
            'pledge_collateral_amount',
            'perfected_intrest_ind',
            'future_income_ind',
            'future_income_desc',
            'future_income_estimate',
            'depository_account_established_date',
            'depository_account_location',
            'depository_account_street_1',
            'depository_account_street_2',
            'depository_account_city',
            'depository_account_state',
            'depository_account_zip',
            'depository_account_auth_date',
            'basis_of_loan_desc',
            'treasurer_entity_id',
            'treasurer_signed_date',
            'authorized_entity_id',
            'authorized_entity_title',
            'authorized_signed_date',
    ]
    try:
        return {k: v for k, v in data.items() if k in valid_fields}
    except:
        raise Exception('invalid request data.')

def check_mandatory_fields_SC1(data):
    """
    validate mandatory fields for sched_a item
    """
    try:
        errors = []
        for field in MANDATORY_FIELDS_SCHED_C1:
            if not(field in data and check_null_value(data.get(field))):
                errors.append(field)
        # if len(error) > 0:
        if errors:
            # string = ""
            # for x in error:
            #     string = string + x + ", "
            # string = string[0:-2]
            raise Exception(
                'The following mandatory fields are required in order to save data to schedA table: {}'.format(','.join(errors)))
    except:
        raise


def put_schedC1(data):
    """
    update sched_c1 item
    here we are assuming lender_entoty_id are always referencing something already in our DB
    """
    try:
        check_mandatory_fields_SC1(data)
        # transaction_id = check_transaction_id(data.get('transaction_id'))
        try:
            put_sql_schedC1(data)
        except Exception as e:
            raise Exception(
                'The put_sql_schedC1 function is throwing an error: ' + str(e))
        return data
    except:
        raise
    
def put_sql_schedC1(data):    
    """
    uopdate a schedule_c2 item
    """
    _sql = """UPDATE public.sched_c1
              SET
                line_number = %s,
                transaction_type = %s,
                transaction_type_identifier = %s,
                lender_entity_id = %s,
                loan_amount = %s,
                loan_intrest_rate = %s,
                loan_incurred_date = %s,
                loan_due_date = %s,
                is_loan_restructured = %s,
                original_loan_date = %s,
                credit_amount_this_draw = %s,
                total_outstanding_balance = %s,
                other_parties_liable = %s,
                pledged_collateral_ind = %s,
                pledge_collateral_desc = %s,
                pledge_collateral_amount=%s,
                perfected_intrest_ind=%s,
                future_income_ind=%s,
                future_income_desc=%s,
                future_income_estimate=%s,
                depository_account_established_date=%s,
                depository_account_location=%s,
                depository_account_street_1=%s,
                depository_account_street_2=%s,
                depository_account_city=%s,
                depository_account_state=%s,
                depository_account_zip=%s,
                depository_account_auth_date=%s,
                basis_of_loan_desc=%s,
                treasurer_entity_id =%s,
                treasurer_signed_date=%s,
                authorized_entity_id=%s,
                authorized_entity_title = %s,
                authorized_signed_date = %s,
                last_update_date = %s
              WHERE transaction_id = %s AND report_id = %s AND cmte_id = %s AND delete_ind is distinct from 'Y'
        """
    _v = (
            data.get('line_number'),
            data.get('transaction_type'),
            data.get('transaction_type_identifier', ''),
            data.get('lender_entity_id', ''),
            data.get('loan_amount', None),
            data.get('loan_intrest_rate', ''),
            data.get('loan_incurred_date', None),
            data.get('loan_due_date', None),
            data.get('is_loan_restructured', ''),
            data.get('original_loan_date', None),
            data.get('credit_amount_this_draw', None),
            data.get('total_outstanding_balance', None),
            data.get('other_parties_liable', ''),
            data.get('pledged_collateral_ind', ''),
            data.get('pledge_collateral_desc', ''),
            data.get('pledge_collateral_amount', None),
            data.get('perfected_intrest_ind', ''),
            data.get('future_income_ind', ''),
            data.get('future_income_desc', ''),
            data.get('future_income_estimate', None),
            data.get('depository_account_established_date', None),
            data.get('depository_account_location', ''),
            data.get('depository_account_street_1', ''),
            data.get('depository_account_street_2', ''),
            data.get('depository_account_city', ''),
            data.get('depository_account_state', ''),
            data.get('depository_account_zip', ''),
            data.get('depository_account_auth_date', None),
            data.get('basis_of_loan_desc', ''),
            data.get('treasurer_entity_id', ''),
            data.get('treasurer_signed_date', None),
            data.get('authorized_entity_id', ''),
            data.get('authorized_entity_title', ''),
            data.get('authorized_signed_date', None),
            datetime.datetime.now(),
            data.get('transaction_id'),
            data.get('report_id'),
            data.get('cmte_id'),
          )
    do_transaction(_sql, _v)



def validate_sc1_data(data):
    """
    check madatory fields for now
    """
    check_mandatory_fields_SC1(data)


def post_schedC1(data):
    """
    function for handling POST request for sc1, need to:
    1. generatye new transaction_id
    2. validate data
    3. save data to db
    """
    try:
        # check_mandatory_fields_SA(datum, MANDATORY_FIELDS_SCHED_A)
        data['transaction_id'] = get_next_transaction_id('SC')
        validate_sc1_data(data)
        try:
            post_sql_schedC1(data)
        except Exception as e:
            raise Exception(
                'The post_sql_schedC1 function is throwing an error: ' + str(e))
        return data
    except:
        raise


def post_sql_schedC1(data):
    try:
        _sql = """
        INSERT INTO public.sched_c1 (
            cmte_id,
            report_id,
            line_number,
            transaction_type,
            transaction_type_identifier,
            transaction_id,
            lender_entity_id,
            loan_amount,
            loan_intrest_rate,
            loan_incurred_date,
            loan_due_date,
            is_loan_restructured,
            original_loan_date,
            credit_amount_this_draw,
            total_outstanding_balance,
            other_parties_liable,
            pledged_collateral_ind,
            pledge_collateral_desc,
            pledge_collateral_amount,
            perfected_intrest_ind,
            future_income_ind,
            future_income_desc,
            future_income_estimate,
            depository_account_established_date,
            depository_account_location,
            depository_account_street_1,
            depository_account_street_2,
            depository_account_city,
            depository_account_state,
            depository_account_zip,
            depository_account_auth_date,
            basis_of_loan_desc,
            treasurer_entity_id,
            treasurer_signed_date,
            authorized_entity_id,
            authorized_entity_title,
            authorized_signed_date,
            create_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """
        _v = (
            data.get('cmte_id'),
            data.get('report_id'),
            data.get('line_number'),
            data.get('transaction_type'),
            data.get('transaction_type_identifier', ''),
            data.get('transaction_id', ''),
            data.get('lender_entity_id', ''),
            data.get('loan_amount', None),
            data.get('loan_intrest_rate', ''),
            data.get('loan_incurred_date', None),
            data.get('loan_due_date', None),
            data.get('is_loan_restructured', ''),
            data.get('original_loan_date', None),
            data.get('credit_amount_this_draw', None),
            data.get('total_outstanding_balance', None),
            data.get('other_parties_liable', ''),
            data.get('pledged_collateral_ind', ''),
            data.get('pledge_collateral_desc', ''),
            data.get('pledge_collateral_amount', None),
            data.get('perfected_intrest_ind', ''),
            data.get('future_income_ind', ''),
            data.get('future_income_desc', ''),
            data.get('future_income_estimate', None),
            data.get('depository_account_established_date', None),
            data.get('depository_account_location', ''),
            data.get('depository_account_street_1', ''),
            data.get('depository_account_street_2', ''),
            data.get('depository_account_city', ''),
            data.get('depository_account_state', ''),
            data.get('depository_account_zip', ''),
            data.get('depository_account_auth_date', None),
            data.get('basis_of_loan_desc', ''),
            data.get('treasurer_entity_id', ''),
            data.get('treasurer_signed_date', None),
            data.get('authorized_entity_id', ''),
            data.get('authorized_entity_title', ''),
            data.get('authorized_signed_date', None),
            datetime.datetime.now(),
        )
        with connection.cursor() as cursor:
            # Insert data into schedD table
            cursor.execute(_sql, _v)
    except Exception:
        raise

def get_schedC1(data):
    try:
        cmte_id = data.get('cmte_id')
        report_id = data.get('report_id')
        if 'transaction_id' in data:
            transaction_id = check_transaction_id(data.get('transaction_id'))
            forms_obj = get_list_schedC1(report_id, cmte_id, transaction_id)
        else:
            forms_obj = get_list_all_schedC1(report_id, cmte_id)
        return forms_obj
    except:
        raise

def get_list_all_schedC1(report_id, cmte_id):
    try:
        with connection.cursor() as cursor:
            # GET single row from schedA table
            _sql = """SELECT json_agg(t) FROM ( SELECT 
            cmte_id,
            report_id,
            line_number,
            transaction_type,
            transaction_type_identifier,
            transaction_id,
            lender_entity_id,
            loan_amount,
            loan_intrest_rate,
            loan_incurred_date,
            loan_due_date,
            is_loan_restructured,
            original_loan_date,
            credit_amount_this_draw,
            total_outstanding_balance,
            other_parties_liable,
            pledged_collateral_ind,
            pledge_collateral_desc,
            pledge_collateral_amount,
            perfected_intrest_ind,
            future_income_ind,
            future_income_desc,
            future_income_estimate,
            depository_account_established_date,
            depository_account_location,
            depository_account_street_1,
            depository_account_street_2,
            depository_account_city,
            depository_account_state,
            depository_account_zip,
            depository_account_auth_date,
            basis_of_loan_desc,
            treasurer_entity_id,
            treasurer_signed_date,
            authorized_entity_id,
            authorized_entity_title,
            authorized_signed_date,
            last_update_date
            FROM public.sched_c1
            WHERE report_id = %s AND cmte_id = %s
            AND delete_ind is distinct from 'Y') t
            """
            cursor.execute(_sql, (report_id, cmte_id))
            schedC2_list = cursor.fetchone()[0]
            if schedC2_list is None:
                raise NoOPError(
                    'No sched_c1 transaction found for report_id {} and cmte_id: {}'.format(report_id, cmte_id))
            merged_list = []
            for dictC2 in schedC2_list:
                merged_list.append(dictC2)
        return merged_list
    except Exception:
        raise 

def get_list_schedC1(report_id, cmte_id, transaction_id):
    try:
        with connection.cursor() as cursor:
            # GET single row from schedA table
            _sql = """SELECT json_agg(t) FROM ( SELECT 
            cmte_id,
            report_id,
            line_number,
            transaction_type,
            transaction_type_identifier,
            transaction_id,
            lender_entity_id,
            loan_amount,
            loan_intrest_rate,
            loan_incurred_date,
            loan_due_date,
            is_loan_restructured,
            original_loan_date,
            credit_amount_this_draw,
            total_outstanding_balance,
            other_parties_liable,
            pledged_collateral_ind,
            pledge_collateral_desc,
            pledge_collateral_amount,
            perfected_intrest_ind,
            future_income_ind,
            future_income_desc,
            future_income_estimate,
            depository_account_established_date,
            depository_account_location,
            depository_account_street_1,
            depository_account_street_2,
            depository_account_city,
            depository_account_state,
            depository_account_zip,
            depository_account_auth_date,
            basis_of_loan_desc,
            treasurer_entity_id,
            treasurer_signed_date,
            authorized_entity_id,
            authorized_entity_title,
            authorized_signed_date,
            last_update_date
            FROM public.sched_c1
            WHERE report_id = %s AND cmte_id = %s AND transaction_id = %s
            AND delete_ind is distinct from 'Y') t
            """
            cursor.execute(_sql, (report_id, cmte_id, transaction_id))
            schedC2_list = cursor.fetchone()[0]
            if schedC2_list is None:
                raise NoOPError(
                    'No sched_c1 transaction found for transaction_id {}'.format(transaction_id))
            merged_list = []
            for dictC2 in schedC2_list:
                merged_list.append(dictC2)
        return merged_list
    except Exception:
        raise 


def delete_schedC1(data):
    """
    function for handling delete request for sc1
    """
    try:
        # check_mandatory_fields_SC2(data)
        delete_sql_schedC1(data.get('cmte_id'), data.get(
            'report_id'), data.get('transaction_id'))
    except Exception as e:
        raise


def delete_sql_schedC1(cmte_id, report_id, transaction_id):
    """
    do delete sql transaction
    """
    _sql = """UPDATE public.sched_c1
            SET delete_ind = 'Y' 
            WHERE transaction_id = %s AND report_id = %s AND cmte_id = %s
        """
    _v = (transaction_id, report_id, cmte_id)
    do_transaction(_sql, _v)


@api_view(['POST', 'GET', 'DELETE', 'PUT'])
def schedC1(request):
    """
    sched_c1 api supporting POST, GET, DELETE, PUT
    """

    # create new sched_c1 transaction
    if request.method == 'POST':
        try:
            cmte_id = request.user.username
            if not('report_id' in request.data):
                raise Exception('Missing Input: Report_id is mandatory')
            # handling null,none value of report_id
            if not (check_null_value(request.data.get('report_id'))):
                report_id = "0"
            else:
                report_id = check_report_id(request.data.get('report_id'))
            # end of handling
            print(cmte_id)
            print(report_id)
            datum = schedC1_sql_dict(request.data)
            datum['report_id'] = report_id
            datum['cmte_id'] = cmte_id
            print(datum)
            if 'transaction_id' in request.data and check_null_value(
                    request.data.get('transaction_id')):
                datum['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
                data = put_schedC1(datum)
            else:
                data = post_schedC1(datum)
            # Associating child transactions to parent and storing them to DB

            output = get_schedC1(data)
            return JsonResponse(output[0], status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response("The schedA API - POST is throwing an exception: "
                            + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        try:
            data = {
                'cmte_id': request.user.username
            }
            if 'report_id' in request.data and check_null_value(request.data.get('report_id')):
                data['report_id'] = check_report_id(
                    request.data.get('report_id'))
            else:
                raise Exception('Missing Input: report_id is mandatory')
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                data['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
            datum = get_schedC1(data)
            return JsonResponse(datum, status=status.HTTP_200_OK, safe=False)
        except NoOPError as e:
            logger.debug(e)
            forms_obj = []
            return JsonResponse(forms_obj, status=status.HTTP_204_NO_CONTENT, safe=False)
        except Exception as e:
            logger.debug(e)
            return Response("The schedC2 API - GET is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        try:
            data = {
                'cmte_id': request.user.username
            }
            if 'report_id' in request.data and check_null_value(request.data.get('report_id')):
                data['report_id'] = check_report_id(
                    request.data.get('report_id'))
            else:
                raise Exception('Missing Input: report_id is mandatory')
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                data['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
            else:
                raise Exception('Missing Input: transaction_id is mandatory')
            delete_schedC1(data)
            return Response("The Transaction ID: {} has been successfully deleted".format(data.get('transaction_id')), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response("The schedD API - DELETE is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        try:
            datum = schedC1_sql_dict(request.data)
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                datum['transaction_id'] = request.data.get('transaction_id')
            else:
                raise Exception('Missing Input: transaction_id is mandatory')

            if not('report_id' in request.data):
                raise Exception('Missing Input: Report_id is mandatory')
            # handling null,none value of report_id
            if not (check_null_value(request.data.get('report_id'))):
                report_id = "0"
            else:
                report_id = check_report_id(request.data.get('report_id'))
            # end of handling
            datum['report_id'] = report_id
            datum['cmte_id'] = request.user.username

            # if 'entity_id' in request.data and check_null_value(request.data.get('entity_id')):
            #     datum['entity_id'] = request.data.get('entity_id')
            # if request.data.get('transaction_type') in CHILD_SCHED_B_TYPES:
            #     data = put_schedB(datum)
            #     output = get_schedB(data)
            # else:
            data = put_schedC1(datum)
            output = get_schedC1(data)
            return JsonResponse(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.debug(e)
            return Response("The schedA API - PUT is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    else:
        raise NotImplementedError

def check_mandatory_fields_SC2(data):
    """
    validate mandatory fields for sched_a item
    """
    try:
        errors = []
        for field in MANDATORY_FIELDS_SCHED_C2:
            if not(field in data and check_null_value(data.get(field))):
                errors.append(field)
        # if len(error) > 0:
        if errors:
            # string = ""
            # for x in error:
            #     string = string + x + ", "
            # string = string[0:-2]
            raise Exception(
                'The following mandatory fields are required in order to save data to schedA table: {}'.format(','.join(errors)))
    except:
        raise


def put_schedC2(data):
    """update sched_c2 item
    here we are assuming guarantor_entoty_id are always referencing something already in our DB
    """
    try:
        check_mandatory_fields_SC2(data)
        transaction_id = check_transaction_id(data.get('transaction_id'))
        try:
            put_sql_schedC2(data)
        except Exception as e:
            raise Exception(
                'The put_sql_schedD function is throwing an error: ' + str(e))
        return data
    except:
        raise


def put_sql_schedC2(data):
    """
    uopdate a schedule_c2 item
    """
    _sql = """UPDATE public.sched_c2
            SET transaction_type_identifier = %s,
                guarantor_entity_id = %s,
                guaranteed_amount = %s,
                last_update_date = %s
            WHERE transaction_id = %s AND report_id = %s AND cmte_id = %s AND delete_ind is distinct from 'Y'
        """
    _v = (data.get('transaction_type_identifier', ''),
          data.get('guarantor_entity_id', ''),
          data.get('guaranteed_amount', ''),
          datetime.datetime.now(),
          data.get('transaction_id'),
          data.get('report_id'),
          data.get('cmte_id'),
          )
    do_transaction(_sql, _v)


def validate_sc2_data(data):
    """validate sc2 json data"""
    check_mandatory_fields_SC2(data)


def post_schedC2(data):
    """
    function for handling POST request, need to:
    1. generatye new transaction_id
    2. validate data
    3. save data to db
    """
    try:
        # check_mandatory_fields_SA(datum, MANDATORY_FIELDS_SCHED_A)
        data['transaction_id'] = get_next_transaction_id('SC')
        validate_sc2_data(data)

        # save entities rirst
        # if 'creditor_entity_id' in datum:
        #     get_data = {
        #         'cmte_id': datum.get('cmte_id'),
        #         'entity_id': datum.get('creditor_entity_id')
        #     }
        #     prev_entity_list = get_entities(get_data)
        #     entity_data = put_entities(datum)
        # else:
        #     entity_data = post_entities(datum)

        # continue to save transaction
        # creditor_entity_id = entity_data.get('creditor_entity_id')
        # datum['creditor_entity_id'] = creditor_entity_id
        # datum['line_number'] = disclosure_rules(datum.get('line_number'), datum.get('report_id'), datum.get('transaction_type'), datum.get('contribution_amount'), datum.get('contribution_date'), entity_id, datum.get('cmte_id'))
        # trans_char = "SD"
        # transaction_id = get_next_transaction_id(trans_char)
        # datum['transaction_id'] = transaction_id
        try:
            post_sql_schedC2(data)
        except Exception as e:
            # if 'creditor_entity_id' in datum:
            #     entity_data = put_entities(prev_entity_list[0])
            # else:
            #     get_data = {
            #         'cmte_id': datum.get('cmte_id'),
            #         'entity_id': creditor_entity_id
            #     }
            #     remove_entities(get_data)
            raise Exception(
                'The post_sql_schedC2 function is throwing an error: ' + str(e))
        # update line number based on aggregate amount info
        # update_linenumber_aggamt_transactions_SA(datum.get('contribution_date'), datum.get(
        #     'transaction_type'), entity_id, datum.get('cmte_id'), datum.get('report_id'))
        return data
    except:
        raise


def post_sql_schedC2(data):
    try:
        _sql = """
        INSERT INTO public.sched_c2 (cmte_id,
                                    report_id,
                                    transaction_type_identifier,
                                    transaction_id,
                                    guarantor_entity_id,
                                    guaranteed_amount,
                                    create_date)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """
        _v = (
            data.get('cmte_id', ''),
            data.get('report_id', ''),
            data.get('transaction_type_identifier', ''),
            data.get('transaction_id', ''),
            data.get('guarantor_entity_id', ''),
            data.get('guaranteed_amount', ''),
            datetime.datetime.now(),
        )
        with connection.cursor() as cursor:
            # Insert data into schedD table
            cursor.execute(_sql, _v)
    except Exception:
        raise


def get_schedC2(data):
    try:
        cmte_id = data.get('cmte_id')
        report_id = data.get('report_id')
        if 'transaction_id' in data:
            transaction_id = check_transaction_id(data.get('transaction_id'))
            forms_obj = get_list_schedC2(report_id, cmte_id, transaction_id)
        else:
            forms_obj = get_list_all_schedC2(report_id, cmte_id)
        return forms_obj
    except:
        raise


def delete_schedC2(data):
    """
    function for handling delete request for sc2
    """
    try:
        check_mandatory_fields_SC2(data)
        delete_sql_schedC2(data.get('cmte_id'), data.get(
            'report_id'), data.get('transaction_id'))
    except Exception as e:
        raise


def delete_sql_schedC2(cmte_id, report_id, transaction_id):
    _sql = """UPDATE public.sched_c2
            SET delete_ind = 'Y' 
            WHERE transaction_id = %s AND report_id = %s AND cmte_id = %s
        """
    _v = (transaction_id, report_id, cmte_id)
    do_transaction(_sql, _v)


def get_list_all_schedC2(report_id, cmte_id):
    try:
        with connection.cursor() as cursor:
            # GET single row from schedA table
            _sql = """SELECT json_agg(t) FROM ( SELECT cmte_id,
            report_id,
            transaction_type_identifier,
            transaction_id,
            guarantor_entity_id,
            guaranteed_amount,
            last_update_date
            FROM public.sched_c2
            WHERE report_id = %s AND cmte_id = %s
            AND delete_ind is distinct from 'Y') t
            """
            cursor.execute(_sql, (report_id, cmte_id))
            schedC2_list = cursor.fetchone()[0]
            if schedC2_list is None:
                raise NoOPError(
                    'No sched_c2 transaction found for report_id {} and cmte_id: {}'.format(report_id, cmte_id))
            merged_list = []
            for dictC2 in schedC2_list:
                merged_list.append(dictC2)
        return merged_list
    except Exception:
        raise


def get_list_schedC2(report_id, cmte_id, transaction_id):
    """
        cmte_id = models.CharField(max_length=9)
    report_id = models.BigIntegerField()
    transaction_type_identifier = models.CharField(
        max_length=12, blank=True, null=True)
    transaction_id = models.CharField(primary_key=True, max_length=20)
    guarantor_entity_id = models.CharField(
        max_length=20, blank=True, null=True)
    guaranteed_amount = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True)
    delete_ind = models.CharField(max_length=1, blank=True, null=True)
    create_date = models.DateTimeField(blank=True, null=True)
    last_update_date = models.DateTimeField(blank=True, null=True)
    """

    try:
        with connection.cursor() as cursor:
            # GET single row from schedA table
            _sql = """SELECT json_agg(t) FROM ( SELECT cmte_id,
            report_id,
            transaction_type_identifier,
            transaction_id,
            guarantor_entity_id,
            guaranteed_amount,
            last_update_date
            FROM public.sched_c2
            WHERE report_id = %s AND cmte_id = %s AND transaction_id = %s
            AND delete_ind is distinct from 'Y') t
            """

            cursor.execute(_sql, (report_id, cmte_id, transaction_id))

            schedC2_list = cursor.fetchone()[0]

            if schedC2_list is None:
                raise NoOPError(
                    'The transaction id: {} does not exist or is deleted'.format(transaction_id))
            merged_list = []
            for dictC2 in schedC2_list:
                merged_list.append(dictC2)
        return merged_list
    except Exception:
        raise


def schedC2_sql_dict(data):
    valid_fields = [
        'transaction_type_identifier',
        'guarantor_entity_id',
        'guaranteed_amount',
    ]
    try:
        return {k: v for k, v in data.items() if k in valid_fields}
    except:
        raise Exception('invalid request data.')


# Create your views here.
#
@api_view(['POST', 'GET', 'DELETE', 'PUT'])
def schedC2(request):
    """
    sched_c2 api supporting POST, GET, DELETE, PUT
    """

    # create new sched_c2 transaction
    if request.method == 'POST':
        try:
            cmte_id = request.user.username
            if not('report_id' in request.data):
                raise Exception('Missing Input: Report_id is mandatory')
            # handling null,none value of report_id
            if not (check_null_value(request.data.get('report_id'))):
                report_id = "0"
            else:
                report_id = check_report_id(request.data.get('report_id'))
            # end of handling
            print(cmte_id)
            print(report_id)
            datum = schedC2_sql_dict(request.data)
            datum['report_id'] = report_id
            datum['cmte_id'] = cmte_id
            if 'transaction_id' in request.data and check_null_value(
                    request.data.get('transaction_id')):
                datum['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
                data = put_schedC2(datum)
            else:
                print(datum)
                data = post_schedC2(datum)
            # Associating child transactions to parent and storing them to DB

            output = get_schedC2(data)
            return JsonResponse(output[0], status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response("The schedA API - POST is throwing an exception: "
                            + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        try:
            data = {
                'cmte_id': request.user.username
            }
            if 'report_id' in request.data and check_null_value(request.data.get('report_id')):
                data['report_id'] = check_report_id(
                    request.data.get('report_id'))
            else:
                raise Exception('Missing Input: report_id is mandatory')
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                data['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
            datum = get_schedC2(data)
            return JsonResponse(datum, status=status.HTTP_200_OK, safe=False)
        except NoOPError as e:
            logger.debug(e)
            forms_obj = []
            return JsonResponse(forms_obj, status=status.HTTP_204_NO_CONTENT, safe=False)
        except Exception as e:
            logger.debug(e)
            return Response("The schedC2 API - GET is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        try:
            data = {
                'cmte_id': request.user.username
            }
            if 'report_id' in request.data and check_null_value(request.data.get('report_id')):
                data['report_id'] = check_report_id(
                    request.data.get('report_id'))
            else:
                raise Exception('Missing Input: report_id is mandatory')
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                data['transaction_id'] = check_transaction_id(
                    request.data.get('transaction_id'))
            else:
                raise Exception('Missing Input: transaction_id is mandatory')
            delete_schedC2(data)
            return Response("The Transaction ID: {} has been successfully deleted".format(data.get('transaction_id')), status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response("The schedC2 API - DELETE is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        try:
            datum = schedC2_sql_dict(request.data)
            if 'transaction_id' in request.data and check_null_value(request.data.get('transaction_id')):
                datum['transaction_id'] = request.data.get('transaction_id')
            else:
                raise Exception('Missing Input: transaction_id is mandatory')

            if not('report_id' in request.data):
                raise Exception('Missing Input: Report_id is mandatory')
            # handling null,none value of report_id
            if not (check_null_value(request.data.get('report_id'))):
                report_id = "0"
            else:
                report_id = check_report_id(request.data.get('report_id'))
            # end of handling
            datum['report_id'] = report_id
            datum['cmte_id'] = request.user.username

            # if 'entity_id' in request.data and check_null_value(request.data.get('entity_id')):
            #     datum['entity_id'] = request.data.get('entity_id')
            # if request.data.get('transaction_type') in CHILD_SCHED_B_TYPES:
            #     data = put_schedB(datum)
            #     output = get_schedB(data)
            # else:
            data = put_schedC2(datum)
            # output = get_schedA(data)
            return JsonResponse(data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.debug(e)
            return Response("The schedA API - PUT is throwing an error: " + str(e), status=status.HTTP_400_BAD_REQUEST)

    else:
        raise NotImplementedError


