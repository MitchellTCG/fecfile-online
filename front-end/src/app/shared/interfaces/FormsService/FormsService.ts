 export interface form99 {
  id: string,
  committeeid: string,
  committeename: string,
  street1: string,
  street2: string,
  city: string,
  state: string,
  zipcode: string,
  treasurerprefix: string,
  treasurerfirstname: string,
  reason: string,
  text: string,
  treasurermiddlename: string,
  treasurerlastname: string,
  treasurersuffix: string,
  signee: string,
  email_on_file: string,
  email_on_file_1: string,
  additional_email_1: string,
  additional_email_2: string,
  created_at: string,
  is_submitted: boolean,
  filename:string,
  form_type:string,
  file:any,
  org_filename?:string,
  org_fileurl?:string,
  printpriview_filename?:string,
  printpriview_fileurl?:string
 }

 export interface Icommittee_forms {
<<<<<<< HEAD
    category?: string,
=======
    category?: string, 
>>>>>>> develop
    form_type?: string,
    form_description?: string,
    form_info?: string,
    due_date?: string,
    cmte_id?:string,
    form_pdf_url?:string,
    form_type_mini?: string,
  }
<<<<<<< HEAD

  export interface form3x_data {
    cashOnHand?: any,
    steps?: any,
    transactionCategories?: string,
    transactionSearchField?: string
  }

=======
 
>>>>>>> develop
