function openModal(messageId) {
    const modal = document.getElementById('customModal');
    modal.style.display = 'block';
    document.getElementById('modalMessageId').value = messageId;
}

function closeModal() {
    document.getElementById('customModal').style.display = 'none';
}

