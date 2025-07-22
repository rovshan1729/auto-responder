// my_custom.js
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.open-modal-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const modal = new bootstrap.Modal(document.getElementById('myModal'))
            modal.show()
        })
    })
})

