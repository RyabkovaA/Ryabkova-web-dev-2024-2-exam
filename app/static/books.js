"use strict"

function fillModal(event) {
    let deleteUrl = event.relatedTarget.dataset.deleteUrl;
    let modalForm = event.target.querySelector("form");
    modalForm.action = deleteUrl;
    let bookName = event.relatedTarget.dataset.bookName; 
    let modalBody = event.target.querySelector("#modal-body-text");
    modalBody.textContent = 'Вы уверены, что хотите удалить книгу ' + bookName + '?'
}

window.onload = function() {
    let deleteModal = document.getElementById("delete-modal");
    deleteModal.addEventListener("show.bs.modal", fillModal);

    var easyMDE = new easyMDE({
        element: document.getElementById('description')
    })

    var easyMDE = new easyMDE({
        element: document.getElementById('review_text')
    })
}