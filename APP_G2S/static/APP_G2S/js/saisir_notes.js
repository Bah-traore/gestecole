document.addEventListener('DOMContentLoaded', () => {
    const classeSelect = document.getElementById('classe-select');
    const matiereSelect = document.getElementById('matiere-select');
    const examenSelect = document.getElementById('examen-select');
    const elevesList = document.getElementById('eleves-list');
    const form = document.querySelector('form');
    const errorMessageDiv = createErrorMessageElement();

    // Création d'un conteneur pour les messages d'erreur
    function createErrorMessageElement() {
        const div = document.createElement('div');
        div.className = 'text-red-500 mt-4 p-2 border rounded hidden';
        div.setAttribute('role', 'alert');
        elevesList.parentNode.insertBefore(div, elevesList.nextSibling);
        return div;
    }

    // Gestion du statut des champs de saisie
    function toggleInputsDisabled(disabled) {
        document.querySelectorAll('.note-input').forEach(input => {
            input.disabled = disabled;
            input.classList[disabled ? 'add' : 'remove']('opacity-50');
        });
        
        // Affichage d'un message contextuel
        if (disabled && !examenSelect.value) {
            showErrorMessage("Veuillez sélectionner un examen pour activer les champs de saisie");
        } else {
            hideErrorMessage();
        }
    }

    // Affichage des messages d'erreur
    function showErrorMessage(message) {
        errorMessageDiv.textContent = message;
        errorMessageDiv.classList.remove('hidden');
    }

    function hideErrorMessage() {
        errorMessageDiv.classList.add('hidden');
        errorMessageDiv.textContent = '';
    }

    // Chargement des élèves avec gestion d'erreurs améliorée
    async function loadStudents() {
        const classeId = classeSelect.value;
        const matiereId = matiereSelect.value;
        const examenId = examenSelect.value;

        if (!classeId || !matiereId || !examenId) {
            elevesList.innerHTML = '';
            toggleInputsDisabled(true);
            return;
        }

        try {
            const response = await fetch(`/api/eleves/?classe=${classeId}&matiere=${matiereId}&examen=${examenId}`);
            
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const data = await response.json();

            elevesList.innerHTML = data.map(eleve => `
                <tr>
                    <td class="px-6 py-4">${eleve.nom_complet}</td>
                    <td class="px-6 py-4 text-center">
                        <input type="number" 
                            min="0" 
                            max="20" 
                            step="0.01"
                            placeholder="0.00"
                            name="note_classe_${eleve.id}" 
                            value="${eleve.note_classe || 0.0}"
                            class="note-input border rounded p-1 w-20"
                            ${examenId ? '' : 'disabled'}
                        >
                    </td>
                    <td class="px-6 py-4 text-center">
                        <input type="number" 
                            min="0" 
                            max="20" 
                            step="0.01"
                            placeholder="0.00"
                            name="note_examen_${eleve.id}" 
                            value="${eleve.note_examen || 0.0}"
                            class="note-input border rounded p-1 w-20"
                            ${examenId ? '' : 'disabled'}
                        >
                    </td>
                </tr>
            `).join('');

            if (examenId) {
                toggleInputsDisabled(false);
                await validateExam();
            } else {
                toggleInputsDisabled(true);
            }
        } catch (error) {
            console.error("Erreur de chargement des élèves:", error);
            toggleInputsDisabled(true);
            showErrorMessage("Impossible de charger la liste des élèves. Veuillez réessayer plus tard.");
        }
    }

    // Validation améliorée de l'examen
    async function validateExam() {
        const examenId = examenSelect.value;
        if (!examenId) return;

        try {
            const response = await fetch(`/api/examens/${examenId}/`);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            
            const examen = await response.json();
            
            const today = new Date();

            // Parse dates in 'YYYY-MM-DD' format to avoid Invalid Date
            function parseDate(dateStr) {
                const [day, month, year] = dateStr.split('-').map(Number);
                return new Date(2000 + year, month - 1, day);
                }

                const startDate = parseDate(examen.date); // "10-05-25" → 10 mai 2025
                const endDate = parseDate(examen.date_fin); // "15-05-25" → 15 mai 2025

                function toDateOnly(date) {
                return new Date(date.getFullYear(), date.getMonth(), date.getDate());
                }

                const todayDate = toDateOnly(new Date()); // 11 mai 2025
                const startDateOnly = toDateOnly(startDate);
                const endDateOnly = toDateOnly(endDate);

                const isDateValid = startDateOnly && endDateOnly 
                && todayDate >= startDateOnly 
                && todayDate <= endDateOnly;

            // const isPeriodValid = examen.periods_active && !examen.periods_clature;
            const isPeriodValid = examen.periode_active && !examen.periode_cloture;

            if (!isDateValid) {
                showErrorMessage("Les notes ne peuvent être modifiées en dehors de la période d'examen");
            } else if (!isPeriodValid) {
                showErrorMessage("La période de saisie est fermée");
            }

            toggleInputsDisabled(!(isDateValid && isPeriodValid));
        } catch (error) {
            console.error("Erreur de validation de l'examen:", error);
            toggleInputsDisabled(true);
            showErrorMessage("Erreur lors de la validation de l'examen");
        }
    }

    // Validation du formulaire améliorée
    form.addEventListener('submit', function(e) {
        const examenId = examenSelect.value;
        if (!examenId) {
            e.preventDefault();
            showErrorMessage('Veuillez sélectionner un examen avant de soumettre le formulaire');
            return;
        }

        let isValid = true;
        document.querySelectorAll('.note-input').forEach(input => {
            input.classList.remove('border-red-500');
            
            const value = parseFloat(input.value);
            
            // Validation des valeurs numériques
            if (isNaN(value) || value < 0 || value > 20) {
                isValid = false;
                input.classList.add('border-red-500');
                input.setAttribute('aria-invalid', 'true');
            } else {
                input.setAttribute('aria-invalid', 'false');
            }
        });

        if (!isValid) {
            e.preventDefault();
            showErrorMessage('Veuillez corriger les erreurs dans les champs rouges');
        }
    });

    // Écouteurs d'événements optimisés
    [classeSelect, matiereSelect, examenSelect].forEach(select => {
        select.addEventListener('change', () => {
            hideErrorMessage();
            loadStudents();
        });
    });

    // Chargement initial
    loadStudents();
});