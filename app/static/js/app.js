document.querySelector('.menu-toggle')?.addEventListener('click', function () {
  const open = this.getAttribute('aria-expanded') !== 'true';
  this.setAttribute('aria-expanded', String(open));
  document.querySelector('#navigation').classList.toggle('open', open);
});
document.querySelectorAll('.dismiss').forEach(button => button.addEventListener('click', () => button.parentElement.remove()));
const dialog = document.querySelector('#confirm-dialog');
let pendingForm = null;
document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', event => {
  event.preventDefault(); pendingForm = form; dialog.returnValue = 'cancel'; dialog.showModal();
}));
dialog?.addEventListener('close', () => { if (dialog.returnValue === 'confirm' && pendingForm) pendingForm.submit(); pendingForm = null; });
const form = document.querySelector('#transaction-form');
if (form) document.querySelector('#tx-type').addEventListener('change', event => {
  const categories = JSON.parse(event.target.value === 'income' ? form.dataset.incomes : form.dataset.expenses);
  document.querySelector('#tx-category').replaceChildren(...categories.map(value => new Option(value, value)));
});
