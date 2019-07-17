import {
  Component,
  EventEmitter,
  ElementRef,
  Input,
  OnInit,
  Output,
  ViewEncapsulation,
  ViewChild
} from '@angular/core';
import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { FormBuilder, FormGroup, FormControl, NgForm, Validators } from '@angular/forms';
import { NgbTooltipConfig } from '@ng-bootstrap/ng-bootstrap';
import { environment } from '../../../../environments/environment';
import { FormsService } from '../../../shared/services/FormsService/forms.service';
import { UtilService } from '../../../shared/utils/util.service';
import { MessageService } from '../../../shared/services/MessageService/message.service';
import { IndividualReceiptService } from './individual-receipt.service';
import { f3xTransactionTypes } from '../../../shared/interfaces/FormsService/FormsService';
import { alphaNumeric } from '../../../shared/utils/forms/validation/alpha-numeric.validator';
import { floatingPoint } from '../../../shared/utils/forms/validation/floating-point.validator';
import { contributionDate } from '../../../shared/utils/forms/validation/contribution-date.validator';
import { ReportTypeService } from '../../../forms/form-3x/report-type/report-type.service';

@Component({
  selector: 'f3x-individual-receipt',
  templateUrl: './individual-receipt.component.html',
  styleUrls: ['./individual-receipt.component.scss'],
  providers: [NgbTooltipConfig, CurrencyPipe, DecimalPipe],
  encapsulation: ViewEncapsulation.None
})
export class IndividualReceiptComponent implements OnInit {
  @Output() status: EventEmitter<any> = new EventEmitter<any>();
  @Input() selectedOptions: any = {};
  @Input() formOptionsVisible: boolean = false;
  @Input() transactionTypeText = '';

  public checkBoxVal: boolean = false;
  public frmIndividualReceipt: FormGroup;
  public formFields: any = [];
  public formVisible: boolean = false;
  public hiddenFields: any = [];
  public memoCode: boolean = false;
  public testForm: FormGroup;
  public titles: any = [];
  public states: any = [];

  private _formType: string = '';
  private _reportType: any = {};
  private _types: any = [];
  private _transaction: any = {};
  private _transactionType: string = null;
  private _formSubmitted: boolean = false;
  private readonly _contributionAggregateValue: number = 0.0;
  private readonly _memoCodeValue: string = 'X';

  constructor(
    private _http: HttpClient,
    private _fb: FormBuilder,
    private _formService: FormsService,
    private _receiptService: IndividualReceiptService,
    private _activatedRoute: ActivatedRoute,
    private _config: NgbTooltipConfig,
    private _router: Router,
    private _utilService: UtilService,
    private _messageService: MessageService,
    private _currencyPipe: CurrencyPipe,
    private _decimalPipe: DecimalPipe,
    private _reportTypeService: ReportTypeService
  ) {
    this._config.placement = 'right';
    this._config.triggers = 'click';
  }

  ngOnInit(): void {
    this._formType = this._activatedRoute.snapshot.paramMap.get('form_id');

    this._messageService.clearMessage();

    this._reportType = JSON.parse(localStorage.getItem(`form_${this._formType}_report_type`));

    if (this._reportType === null || typeof this._reportType === 'undefined') {
      this._reportType = JSON.parse(localStorage.getItem(`form_${this._formType}_report_type_backup`));
    }

    this.frmIndividualReceipt = this._fb.group({});

    this._receiptService.getDynamicFormFields(this._formType, 'Individual Receipt').subscribe(res => {
      if (res) {
        if (res.hasOwnProperty('data')) {
          if (typeof res.data === 'object') {
            if (res.data.hasOwnProperty('formFields')) {
              if (Array.isArray(res.data.formFields)) {
                this.formFields = res.data.formFields;

                this._setForm(this.formFields);
              }
            }
            if (res.data.hasOwnProperty('hiddenFields')) {
              if (Array.isArray(res.data.hiddenFields)) {
                this.hiddenFields = res.data.hiddenFields;
              }
            }
            if (res.data.hasOwnProperty('states')) {
              if (Array.isArray(res.data.states)) {
                this.states = res.data.states;
              }
            }
            if (res.data.hasOwnProperty('titles')) {
              if (Array.isArray(res.data.titles)) {
                this.titles = res.data.titles;
              }
            }
          } // typeof res.data
        } // res.hasOwnProperty('data')
      } // res
    });
  }

  ngDoCheck(): void {
    if (this.selectedOptions) {
      if (this.selectedOptions.length >= 1) {
        this.formVisible = true;
      }
    }

    this._validateContributionDate();

    this._getTransactionType();
  }

  ngOnDestroy(): void {
    this._messageService.clearMessage();
  }

  public debug(obj: any): void {
    console.log('obj: ', obj);
  }

  /**
   * Generates the dynamic form after all the form fields are retrived.
   *
   * @param      {Array}  fields  The fields
   */
  private _setForm(fields: any): void {
    const formGroup: any = [];

    fields.forEach(el => {
      if (el.hasOwnProperty('cols')) {
        el.cols.forEach(e => {
          formGroup[e.name] = new FormControl(e.value || null, this._mapValidators(e.validation, e.name));
        });
      }
    });

    this.frmIndividualReceipt = new FormGroup(formGroup);
  }

  /**
   * Sets the form field valition requirements.
   *
   * @param      {Object} validators  The validators.
   * @param      {String} fieldName The name of the field.
   * @return     {Array}  The validations in an Array.
   */
  private _mapValidators(validators: any, fieldName: string): Array<any> {
    const formValidators = [];

    /**
     * Adds alphanumeric validation for the zip code field.
     */
    if (fieldName === 'zip_code') {
      formValidators.push(alphaNumeric());
    }

    if (validators) {
      for (const validation of Object.keys(validators)) {
        if (validation === 'required') {
          if (validators[validation]) {
            formValidators.push(Validators.required);
          }
        } else if (validation === 'min') {
          if (validators[validation] !== null) {
            formValidators.push(Validators.minLength(validators[validation]));
          }
        } else if (validation === 'max') {
          if (validators[validation] !== null) {
            formValidators.push(Validators.maxLength(validators[validation]));
          }
        } else if (validation === 'dollarAmount') {
          if (validators[validation] !== null) {
            formValidators.push(floatingPoint());
          }
        }
      }
    }

    return formValidators;
  }

  /**
   * Validates the contribution date selected.
   */
  private _validateContributionDate(): void {
    this._reportType = JSON.parse(localStorage.getItem(`form_${this._formType}_report_type`));

    if (this._reportType !== null) {
      const cvgStartDate: string = this._reportType.cvgStartDate;
      const cvgEndDate: string = this._reportType.cvgEndDate;

      if (this.memoCode) {
        this.frmIndividualReceipt.controls['contribution_date'].setValidators([Validators.required]);

        this.frmIndividualReceipt.controls['contribution_date'].updateValueAndValidity();
      } else {
        if (this.frmIndividualReceipt.controls['contribution_date']) {
          this.frmIndividualReceipt.controls['contribution_date'].setValidators([
            contributionDate(cvgStartDate, cvgEndDate),
            Validators.required
          ]);

          this.frmIndividualReceipt.controls['contribution_date'].updateValueAndValidity();
        }
      }
    }

    if (this.frmIndividualReceipt) {
      if (this.frmIndividualReceipt.controls['contribution_amount']) {
        this.frmIndividualReceipt.controls['contribution_amount'].setValidators([floatingPoint(), Validators.required]);

        this.frmIndividualReceipt.controls['contribution_amount'].updateValueAndValidity();
      }

      if (this.frmIndividualReceipt.controls['contribution_aggregate']) {
        this.frmIndividualReceipt.controls['contribution_aggregate'].setValidators([floatingPoint()]);

        this.frmIndividualReceipt.controls['contribution_aggregate'].updateValueAndValidity();
      }
    }
  }

  /**
   * Gets the transaction type.
   */
  private _getTransactionType(): void {
    const transactionType: any = JSON.parse(localStorage.getItem(`form_${this._formType}_transaction_type`));

    if (typeof transactionType === 'object') {
      if (transactionType !== null) {
        if (transactionType.hasOwnProperty('mainTransactionTypeValue')) {
          this._transactionType = transactionType.mainTransactionTypeValue;
        }
      }
    }
  }

  /**
   * Updates the contribution aggregate field once contribution ammount is entered.
   *
   * @param      {Object}  e       The event object.
   */
  public contributionAmountChange(e): void {
    const contributionAmount: string = e.target.value;
    const contributionAggregate: string = String(this._contributionAggregateValue);
    /**
     * TODO: Look into why read only input returns null.
     */
    if (!this.memoCode) {
      const total: number = parseFloat(contributionAmount) + parseFloat(contributionAggregate);
      const value: string = this._decimalPipe.transform(total, '.2-2');

      this.frmIndividualReceipt.controls['contribution_aggregate'].setValue(value);
    }

    /**
     * TODO: To be implemented in the future.
     */

    // this._receiptService
    //   .aggregateAmount(
    //     res.report_id,
    //     res.transaction_type,
    //     res.contribution_date,
    //     res.entity_id,
    //     res.contribution_amount
    //   )
    //   .subscribe(resp => {
    //     console.log('resp: ', resp);
    //   });
  }

  /**
   * Updates vaprivate _memoCode variable.
   *
   * @param      {Object}  e      The event object.
   */
  public memoCodeChange(e): void {
    const { checked } = e.target;

    if (checked) {
      this.memoCode = checked;
      console.log('this.memoCode: ', this.memoCode);
    } else {
      this._validateContributionDate();
      this.memoCode = checked;
    }
  }

  /**
   * Vaidates the form on submit.
   */
  public doValidateReceipt() {
    if (this.frmIndividualReceipt.valid) {
      const receiptObj: any = {};

      for (const field in this.frmIndividualReceipt.controls) {
        if (field === 'contribution_date') {
          receiptObj[field] = this._utilService.formatDate(this.frmIndividualReceipt.get(field).value);
        } else {
          if (field === 'memo_code') {
            if (this.memoCode) {
              receiptObj[field] = this.frmIndividualReceipt.get(field).value;
            }
          } else {
            receiptObj[field] = this.frmIndividualReceipt.get(field).value;
          }
        }
      }

      this.hiddenFields.forEach(el => {
        receiptObj[el.name] = el.value;
      });

      localStorage.setItem(`form_${this._formType}_receipt`, JSON.stringify(receiptObj));

      this._receiptService.saveSchedule(this._formType).subscribe(res => {
        if (res) {
          if (res.hasOwnProperty('memo_code')) {
            if (typeof res.memo_code === 'object') {
              if (res.memo_code === null) {
                this._receiptService.getSchedule(this._formType, res).subscribe(resp => {
                  const message: any = {
                    formType: this._formType,
                    totals: resp
                  };

                  this._messageService.sendMessage(message);
                });
              }
            }
          }

          this._formSubmitted = true;
          this.memoCode = false;
          this.frmIndividualReceipt.reset();
          this.frmIndividualReceipt.controls['contribution_aggregate'].setValue(this._contributionAggregateValue);
          this.frmIndividualReceipt.controls['memo_code'].setValue(this._memoCodeValue);

          localStorage.removeItem(`form_${this._formType}_receipt`);

          window.scrollTo(0, 0);
        }
      });
    } else {
      this.frmIndividualReceipt.markAsDirty();
      this.frmIndividualReceipt.markAsTouched();
      window.scrollTo(0, 0);
    }
  }

  /**
   * Goes to the previous step.
   */
  public previousStep(): void {
    this.status.emit({
      form: {},
      direction: 'previous',
      step: 'step_2'
    });
  }

  /**
   * Navigate to the Transactions.
   */
  public viewTransactions(): void {
    let reportId = '0';
    let form3XReportType = JSON.parse(localStorage.getItem(`form_${this._formType}_report_type`));

    if (form3XReportType === null || typeof form3XReportType === 'undefined') {
      form3XReportType = JSON.parse(localStorage.getItem(`form_${this._formType}_report_type_backup`));
    }

    console.log('viewTransactions form3XReportType', form3XReportType);

    if (typeof form3XReportType === 'object' && form3XReportType !== null) {
      if (form3XReportType.hasOwnProperty('reportId')) {
        reportId = form3XReportType.reportId;
      } else if (form3XReportType.hasOwnProperty('reportid')) {
        reportId = form3XReportType.reportid;
      }
    }

    console.log('reportId', reportId);

    if (!reportId) {
      reportId = '0';
      // reportId = '431';
      // reportId = '1206963';
    }
    console.log(`View Transactions for form ${this._formType} where reportId = ${reportId}`);

    this._router.navigate([`/forms/transactions/${this._formType}/${reportId}`]);
  }

  public printPreview(): void {
    this._reportTypeService.signandSaveSubmitReport('3X', 'Saved');
    this._reportTypeService.printPreviewPdf('3X', 'PrintPreviewPDF').subscribe(
      res => {
        if (res) {
          console.log('Accessing FinancialSummaryComponent printPriview res ...', res);

          if (res['results.pdf_url'] !== null) {
            console.log("res['results.pdf_url'] = ", res['results.pdf_url']);
            window.open(res.results.pdf_url, '_blank');
          }
        }
      },
      error => {
        console.log('error: ', error);
      }
    ); /*  */
  }
}
