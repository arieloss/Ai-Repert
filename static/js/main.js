document.addEventListener('DOMContentLoaded', () => {
    // Handle charge name update forms
    const nameForms = document.querySelectorAll('form.update-charge-name');
    nameForms.forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const chargeId = form.getAttribute('data-charge-id');
            const nomInput = form.querySelector('input[name="nom"]');
            const newName = nomInput.value.trim();
            const alertSuccess = form.closest('tr').querySelector('.alert-success');
            const alertError = form.closest('tr').querySelector('.alert-error');

            if (!newName) {
                showAlert(alertError, 'Le nom ne peut pas être vide');
                return;
            }

            try {
                const response = await fetch(`/api/charges/${chargeId}/nom`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nom: newName })
                });

                if (response.ok) {
                    showAlert(alertSuccess, `Nom modifié avec succès: ${newName}`);
                } else {
                    const error = await response.json();
                    showAlert(alertError, `Erreur: ${error.detail || 'Échec de la mise à jour'}`);
                }
            } catch (error) {
                showAlert(alertError, 'Erreur réseau: impossible de contacter le serveur');
            }
        });
    });

    // Handle charge state toggles
    const stateLinks = document.querySelectorAll('.toggle-state');
    stateLinks.forEach(link => {
        link.addEventListener('click', async (e) => {
            e.preventDefault();
            const url = link.getAttribute('href');
            const chargeId = link.getAttribute('data-charge-id');
            const stateSpan = link.closest('tr').querySelector('.state-span');
            const alertSuccess = link.closest('tr').querySelector('.alert-success');
            const alertError = link.closest('tr').querySelector('.alert-error');

            try {
                const response = await fetch(url, { method: 'PUT' });
                if (response.ok) {
                    const data = await response.json();
                    const newState = data.etat ? 'ON' : 'OFF';
                    stateSpan.innerHTML = data.etat
                        ? `<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">ON</span>`
                        : `<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">OFF</span>`;
                    link.textContent = data.etat ? 'Éteindre' : 'Allumer';
                    link.setAttribute('href', `/api/charges/${chargeId}/etat?etat=${!data.etat}`);
                    showAlert(alertSuccess, `État modifié: ${newState}`);
                } else {
                    const error = await response.json();
                    showAlert(alertError, `Erreur: ${error.detail || 'Échec de la mise à jour'}`);
                }
            } catch (error) {
                showAlert(alertError, 'Erreur réseau: impossible de contacter le serveur');
            }
        });
    });

    // Utility function to show alerts
    function showAlert(element, message) {
        element.textContent = message;
        element.style.display = 'block';
        setTimeout(() => {
            element.style.display = 'none';
        }, 3000);
    }
});