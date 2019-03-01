import { Component, Input, OnInit, ViewEncapsulation, ViewChild, OnDestroy } from '@angular/core';
import { style, animate, transition, trigger } from '@angular/animations';
import { PaginationInstance } from 'ngx-pagination';
import { ModalDirective } from 'ngx-bootstrap/modal';
import { TransactionModel } from '../model/transaction.model';
import { SortableColumnModel } from 'src/app/shared/services/TableService/sortable-column.model';
import { TransactionsService, GetTransactionsResponse } from '../service/transactions.service';
import { TableService } from 'src/app/shared/services/TableService/table.service';
import { UtilService } from 'src/app/shared/utils/util.service';
import { ActiveView } from '../transactions.component';
import { TransactionsMessageService } from '../service/transactions-message.service';
import { Subscription } from 'rxjs/Subscription';
import { ConfirmModalComponent } from 'src/app/shared/partials/confirm-modal/confirm-modal.component';
import { DialogService } from 'src/app/shared/services/DialogService/dialog.service';



@Component({
  selector: 'app-transactions-table',
  templateUrl: './transactions-table.component.html',
  styleUrls: ['./transactions-table.component.scss'],
  encapsulation: ViewEncapsulation.None,
  animations: [
    trigger('fadeInOut', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate(500, style({ opacity: 1 }))
      ]),
      transition(':leave', [
        animate(10, style({ opacity: 0 }))
      ])
    ])
  ]
})
export class TransactionsTableComponent implements OnInit, OnDestroy {

  @ViewChild('columnOptionsModal')
  public columnOptionsModal: ModalDirective;

  @Input()
  public formType: string;

  @Input()
  public tableType: string;

  public transactionsModel: Array<TransactionModel>;
  public totalAmount: number;
  public transactionsView = ActiveView.transactions;
  public recycleBinView = ActiveView.recycleBin;

  // Local Storage Keys
  private readonly sortableColumnsLSK: string = 'transactions.sortableColumn';
  private readonly transactionCurrentSortedColLSK: string =
    'transactions.trx.currentSortedColumn';
  private readonly recycleCurrentSortedColLSK: string =
    'transactions.recycle.currentSortedColumn';
  private readonly transactionPageLSK: string =
    'transactions.trx.page';
  private readonly recyclePageLSK: string =
    'transactions.recycle.page';

  /**.
	 * Array of columns to be made sortable.
	 */
  private sortableColumns: SortableColumnModel[] = [];

  /**
	 * A clone of the sortableColumns for reverting user
   * column options on a Cancel.
	 */
  private cloneSortableColumns: SortableColumnModel[] = [];

  /**
	 * Identifies the column currently sorted by name.
	 */
  private currentSortedColumnName: string;

  /**
   * Subscription for messags sent from the parent component to show the PIN Column
   * options.
   */
  private showPinColumnsSubscription: Subscription;

  // ngx-pagination config
  public maxItemsPerPage = 100;
  public directionLinks = false;
  public autoHide = true;
  public config: PaginationInstance;
  public numberOfPages = 0;

  private columnOptionCount = 0;
  private readonly maxColumnOption = 5;
  private allTransactionsSelected: boolean;

  constructor(
    private _transactionsService: TransactionsService,
    private _transactionsMessageService: TransactionsMessageService,
    private _tableService: TableService,
    private _utilService: UtilService,
    private _dialogService: DialogService,
  ) {
    this.showPinColumnsSubscription = this._transactionsMessageService.getMessage().subscribe(
      message => {
        this.showPinColumns();
      }
    );
  }


  /**
   * Initialize the component.
   */
  public ngOnInit(): void {

    const paginateConfig: PaginationInstance = {
      id: 'forms__trx-table-pagination',
      itemsPerPage: 5,
      currentPage: 1
    };
    this.config = paginateConfig;

    // If cached sortableColumns settings in local storage, use it.
    // And get other cached values.
    const sortableColumnsJson: string | null = localStorage.getItem(this.sortableColumnsLSK);
    if (localStorage.getItem(this.sortableColumnsLSK) != null) {
      this.applyCachedValues();
    } else {
      this.setSortableColumns();
    }
    this.cloneSortableColumns = this._utilService.deepClone(this.sortableColumns);

    for (const col of this.sortableColumns) {
      if (col.checked) {
        this.columnOptionCount++;
      }
    }

    this.setSortDefault();
    this.getPage(this.config.currentPage);
  }


  /**
   * When component is destroyed, save off user column options to be applied upon return.
   */
  public ngOnDestroy(): void {
    this.setCachedValues();
    this.showPinColumnsSubscription.unsubscribe();
  }


  /**
	 * The Transactions for a given page.
	 *
	 * @param page the page containing the transactions to get
	 */
  public getPage(page: number): void {
    switch (this.tableType) {
      case this.transactionsView:
        this.getTransactionsPage(page);
        break;
      case this.recycleBinView:
        this.getRecyclingPage(page);
        break;
      default:
        break;
    }
  }


  /**
	 * The Transactions for a given page.
	 *
	 * @param page the page containing the transactions to get
	 */
  public getTransactionsPage(page: number): void {

    this.config.currentPage = page;

    const sortedCol: SortableColumnModel =
      this._tableService.findCurrentSortedColumn(this.currentSortedColumnName, this.sortableColumns);

    this._transactionsService.getFormTransactions(this.formType, page, this.config.itemsPerPage,
      this.currentSortedColumnName, sortedCol.descending)
      .subscribe((res: GetTransactionsResponse) => {
        this.transactionsModel = res.transactions;
        this.totalAmount = res.totalAmount;
        this.config.totalItems = res.totalTransactionCount;
        this.allTransactionsSelected = false;
      });
  }


  /**
	 * The Transactions for the recycling bin.
	 *
	 * @param page the page containing the transactions to get
	 */
  public getRecyclingPage(page: number): void {
    this.calculateNumberOfPages();
    this._transactionsService.getUserDeletedTransactions(this.formType)
      .subscribe((res: GetTransactionsResponse) => {
        this.transactionsModel = res.transactions;
        this.config.totalItems = res.totalTransactionCount;

        // If a row was deleted, the current page may be greated than the last page
        // as result of the delete.
        this.config.currentPage = (page > this.numberOfPages && this.numberOfPages !== 0)
          ? this.numberOfPages : page;
      });
  }


  /**
	 * Wrapper method for the table service to set the class for sort column styling.
	 *
	 * @param colName the column to apply the class
	 * @returns string of classes for CSS styling sorted/unsorted classes
	 */
  public getSortClass(colName: string): string {
    return this._tableService.getSortClass(colName, this.currentSortedColumnName, this.sortableColumns);
  }


  /**
	 * Change the sort direction of the table column.
	 *
	 * @param colName the column name of the column to sort
	 */
  public changeSortDirection(colName: string): void {
    this.currentSortedColumnName = this._tableService.changeSortDirection(colName, this.sortableColumns);

    // TODO this could be done client side or server side.
    // call server for page data in new direction
    this.getPage(this.config.currentPage);
  }


  /**
   * Get the SortableColumnModel by name.
   *
   * @param colName the column name in the SortableColumnModel.
   * @returns the SortableColumnModel matching the colName.
   */
  public getSortableColumn(colName: string): SortableColumnModel {
    for (const col of this.sortableColumns) {
      if (col.colName === colName) {
        return col;
      }
    }
    return new SortableColumnModel('', false, false, false, false);
  }


  /**
   * Determine if the column is to be visible in the table.
   *
   * @param colName
   * @returns true if visible
   */
  public isColumnVisible(colName: string): boolean {
    const sortableCol = this.getSortableColumn(colName);
    if (sortableCol) {
      return sortableCol.visible;
    } else {
      return false;
    }
  }


  /**
   * Set the visibility of a column in the table.
   *
   * @param colName the name of the column to make shown
   * @param visible is true if the columns should be shown
   */
  public setColumnVisible(colName: string, visible: boolean) {
    const sortableCol = this.getSortableColumn(colName);
    if (sortableCol) {
      sortableCol.visible = visible;
    }
  }


  /**
   * Set the checked property of a column in the table.
   * The checked is true if the column option settings
   * is checked for the column.
   *
   * @param colName the name of the column to make shown
   * @param checked is true if the columns should be shown
   */
  private setColumnChecked(colName: string, checked: boolean) {
    const sortableCol = this.getSortableColumn(colName);
    if (sortableCol) {
      sortableCol.checked = checked;
    }
  }


  /**
   *
   * @param colName Determine if the checkbox column option should be disabled.
   */
  public disableOption(colName: string): boolean {
    const sortableCol = this.getSortableColumn(colName);
    if (sortableCol) {
      if (!sortableCol.checked && this.columnOptionCount >
        (this.maxColumnOption - 1)) {
        return true;
      }
    }
    return false;
  }


  /**
   * Toggle the visibility of a column in the table.
   *
   * @param colName the name of the column to toggle
   * @param e the click event
   */
  public toggleVisibility(colName: string, e: any) {

    if (!this.sortableColumns) {
      return;
    }

    // only permit 5 checked at a time
    if (e.target.checked === true) {
      this.columnOptionCount = 0;
      for (const col of this.sortableColumns) {
        if (col.checked) {
          this.columnOptionCount++;
        }
        if (this.columnOptionCount > 5) {
          this.setColumnChecked(colName, false);
          e.target.checked = false;
          this.columnOptionCount--;
          return;
        }
      }
    } else {
      this.columnOptionCount--;
    }

    this.applyDisabledColumnOptions();
  }


  /**
   * Disable the unchecked column options if the max is met.
   */
  private applyDisabledColumnOptions() {
    if (this.columnOptionCount > (this.maxColumnOption - 1)) {
      for (const col of this.sortableColumns) {
        col.disabled = !col.checked;
      }
    } else {
      for (const col of this.sortableColumns) {
        col.disabled = false;
      }
    }
  }


  /**
   * Save the columns to show selected by the user.
   */
  public saveColumnOptions() {

    for (const col of this.sortableColumns) {
      this.setColumnVisible(col.colName, col.checked);
    }
    this.cloneSortableColumns = this._utilService.deepClone(this.sortableColumns);
    this.columnOptionsModal.hide();
  }


  /**
   * Cancel the request to save columns options.
   */
  public cancelColumnOptions() {
    this.columnOptionsModal.hide();
    this.sortableColumns = this._utilService.deepClone(this.cloneSortableColumns);
  }


  /**
   * Toggle checking all types.
   *
   * @param e the click event
   */
  public toggleAllTypes(e: any) {
    const checked = (e.target.checked) ? true : false;
    for (const col of this.sortableColumns) {
      this.setColumnVisible(col.colName, checked);
    }
  }


  /**
	 * Determine if pagination should be shown.
	 */
  public showPagination(): boolean {
    if (this.config.totalItems > this.config.itemsPerPage) {
      return true;
    }
    // otherwise, no show.
    return false;
  }


  /**
   * View all transactions selected by the user.
   */
  public viewAllSelected(): void {
    alert('View all transactions is not yet supported');
  }


  /**
   * Print all transactions selected by the user.
   */
  public printAllSelected(): void {
    alert('Print all transactions is not yet supported');
  }


  /**
   * Export all transactions selected by the user.
   */
  public exportAllSelected(): void {
    alert('Export all transactions is not yet supported');
  }


  /**
   * Link all transactions selected by the user.
   */
  public linkAllSelected(): void {
    alert('Link multiple transaction requirements have not been finalized');
  }


  /**
   * Trash all transactions selected by the user.
   */
  public trashAllSelected(): void {
    alert('Trash all transactions is not yet supported');
  }


  /**
   * Clone the transaction selected by the user.
   *
   * @param trx the Transaction to clone
   */
  public cloneTransaction(): void {
    alert('Clone transaction is not yet supported');
  }


  /**
   * Link the transaction selected by the user.
   *
   * @param trx the Transaction to link
   */
  public linkTransaction(): void {
    alert('Link requirements have not been finalized');
  }


  /**
   * View the transaction selected by the user.
   *
   * @param trx the Transaction to view
   */
  public viewTransaction(): void {
    alert('View transaction is not yet supported');
  }


  /**
   * Edit the transaction selected by the user.
   *
   * @param trx the Transaction to edit
   */
  public editTransaction(): void {
    alert('Edit transaction is not yet supported');
  }


  /**
   * Trash the transaction selected by the user.
   *
   * @param trx the Transaction to trash
   */
  public trashTransaction(): void {
    alert('Trash transaction is not yet supported');
  }


  /**
   * Restore a trashed transaction from the recyle bin.
   *
   * @param trx the Transaction to restore
   */
  public restoreTransaction(trx: TransactionModel): void {

    this._dialogService
      .confirm('You are about to restore transaction ' + trx.transactionId, ConfirmModalComponent)
      .then(res => {
        if (res === 'okay') {
          this._transactionsService.restoreTransaction(trx)
            .subscribe((res: GetTransactionsResponse) => {
              this.getRecyclingPage(this.config.currentPage);
            });
        } else if (res === 'cancel') {
        }
      });
  }


  /**
   * Determine the item range shown by the server-side pagination.
   */
  public determineItemRange(): string {

    let start = 0;
    let end = 0;
    this.numberOfPages = 0;
    this.config.currentPage = this._utilService.isNumber(this.config.currentPage) ?
      this.config.currentPage : 1;

    if (!this.transactionsModel) {
      return;
    }

    if (this.config.currentPage > 0 && this.config.itemsPerPage > 0
      && this.transactionsModel.length > 0) {
      this.calculateNumberOfPages();

      if (this.config.currentPage === this.numberOfPages) {
        end = this.transactionsModel.length;
        start = (this.config.currentPage - 1) * this.config.itemsPerPage + 1;
      } else {
        end = this.config.currentPage * this.config.itemsPerPage;
        start = (end - this.config.itemsPerPage) + 1;
      }
    }
    return start + ' - ' + end;
  }


  /**
   * Show the option to select/deselect columns in the table.
   */
  public showPinColumns() {
    this.applyDisabledColumnOptions();
    this.columnOptionsModal.show();
  }


  /**
   * Check/Uncheck all transactions in the table.
   */
  public changeAllTransactionsSelected() {
    for (const t of this.transactionsModel) {
      t.selected = this.allTransactionsSelected;
    }
  }


  /**
   * Check if the view to show is Transactions.
   */
  public isTransactionViewActive() {
    return this.tableType === this.transactionsView ? true : false;
  }


  /**
   * Check if the view to show is Recycle Bin.
   */
  public isRecycleBinViewActive() {
    return this.tableType === this.recycleBinView ? true : false;
  }


  /**
   * Apply cached values in local storage to the component's class variables.
   */
  private applyCachedValues(): void {
    const sortableColumnsJson: string | null = localStorage.getItem(this.sortableColumnsLSK);
    if (localStorage.getItem(this.sortableColumnsLSK) != null) {
      this.sortableColumns = JSON.parse(sortableColumnsJson);
    } else {
      // Just in case cache has an unexpected issue, use default.
      this.setSortableColumns();
    }

    if (this.isTransactionViewActive()) {

      const currentSortedColumnJson: string | null =
        localStorage.getItem(this.transactionCurrentSortedColLSK);
      let currentSortedColumnL: SortableColumnModel = null;
      if (currentSortedColumnJson) {
        currentSortedColumnL = JSON.parse(currentSortedColumnJson);

        // sort by the column direction previously set
        this.currentSortedColumnName = this._tableService.setSortDirection(currentSortedColumnL.colName,
          this.sortableColumns, currentSortedColumnL.descending);
      } else {
        this.setSortDefault();
      }
      this.applyCurrentSortedColCache(this.transactionCurrentSortedColLSK);
      this.applyCurrentPageCache(this.transactionPageLSK);

    } else if (this.isRecycleBinViewActive()) {
      this.applyCurrentSortedColCache(this.recycleCurrentSortedColLSK);
      this.applyCurrentPageCache(this.recyclePageLSK);
    } else {
    }
  }


  /**
   * Get the current sorted column from the cache and apply it to the component.
   * @param key the key to the value in the local storage cache
   */
  private applyCurrentSortedColCache(key: string) {
    const currentSortedColumnJson: string | null =
      localStorage.getItem(key);
    let currentSortedColumnL: SortableColumnModel = null;
    if (currentSortedColumnJson) {
      currentSortedColumnL = JSON.parse(currentSortedColumnJson);

      // sort by the column direction previously set
      this.currentSortedColumnName = this._tableService.setSortDirection(currentSortedColumnL.colName,
        this.sortableColumns, currentSortedColumnL.descending);
    } else {
      this.setSortDefault();
    }
  }


  /**
   * Get the current page from the cache and apply it to the component.
   * @param key the key to the value in the local storage cache
   */
  private applyCurrentPageCache(key: string) {
    const currentPageCache: string =
      localStorage.getItem(key);
    if (this._utilService.isNumber(currentPageCache)) {
      this.config.currentPage = this._utilService.toInteger(currentPageCache);
    } else {
      this.config.currentPage = 1;
    }
  }

  /**
   * Retrieve the cahce values from local storage and set the
   * component's class variables.
   */
  private setCachedValues() {

    // shared between trx and recycle tables
    localStorage.setItem(this.sortableColumnsLSK,
      JSON.stringify(this.sortableColumns));

    const currentSortedCol = this._tableService.findCurrentSortedColumn(
      this.currentSortedColumnName, this.sortableColumns);

    if (this.isTransactionViewActive()) {

      if (currentSortedCol) {
        localStorage.setItem(this.transactionCurrentSortedColLSK,
          JSON.stringify(currentSortedCol));
      }

      localStorage.setItem(this.transactionPageLSK, this.config.currentPage.toString());
    } else if (this.isRecycleBinViewActive()) {

      if (currentSortedCol) {
        localStorage.setItem(this.recycleCurrentSortedColLSK,
          JSON.stringify(currentSortedCol));
      }
      localStorage.setItem(this.recyclePageLSK, this.config.currentPage.toString());
    } else {
    }
  }


  /**
   * Set the Table Columns model.
   */
  private setSortableColumns(): void {
    // sort column names must match the domain model names
    const defaultSortColumns = ['type', 'transactionId', 'name', 'date', 'amount'];
    const otherSortColumns = ['street', 'city', 'state', 'zip', 'aggregate', 'purposeDescription',
      'contributorEmployer', 'contributorOccupation', 'memoCode', 'memoText'];

    this.sortableColumns = [];
    for (const field of defaultSortColumns) {
      this.sortableColumns.push(new SortableColumnModel(field, false, true, true, false));
    }
    for (const field of otherSortColumns) {
      this.sortableColumns.push(new SortableColumnModel(field, false, false, false, true));
    }
  }


  /**
   * Set the UI to show the default column sorted in the default direction.
   */
  private setSortDefault(): void {
    this.currentSortedColumnName = this._tableService.setSortDirection('type',
      this.sortableColumns, false);
  }


  private calculateNumberOfPages(): void {

    if (this.config.currentPage > 0 && this.config.itemsPerPage > 0) {
      if (this.transactionsModel && this.transactionsModel.length > 0) {
        this.numberOfPages = this.transactionsModel.length / this.config.itemsPerPage;
        this.numberOfPages = Math.ceil(this.numberOfPages);
      }
    }
  }

}