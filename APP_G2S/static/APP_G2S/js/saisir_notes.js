document.addEventListener('DOMContentLoaded', () => {
    const classeSelect = document.getElementById('classe-select');
    const matiereSelect = document.getElementById('matiere-select');
    const examenSelect = document.getElementById('examen-select');
    const elevesList = document.getElementById('eleves-list');

    async function loadStudents() {
        const classeId = classeSelect.value;
        const matiereId = matiereSelect.value;
        const examenId = examenSelect.value;

        if (!classeId || !matiereId) return;

        try {
            const response = await fetch(`/api/eleves/?classe=${classeId}&matiere=${matiereId}&examen=${examenId}`);
            const data = await response.json();

            console.log('Data fetched:', data); // Debugging line
            
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
                        ${eleve.disabled ? 'disabled' : ''}>
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
                        ${eleve.disabled ? 'disabled' : ''}>
                    </td>
                </tr>
            `).join('');
        } catch (error) {
            console.error("Erreur de chargement des élèves:", error);
        }
    }

    async function validateExam() {
        const examenId = examenSelect.value;
        if (!examenId) return;

        try {
            const response = await fetch(`/api/examens/${examenId}/`);
            const examen = await response.json();
            
            const today = new Date();
            const startDate = new Date(examen.date);
            const endDate = new Date(examen.date_fin);

            const isDateValid = today >= startDate && today <= endDate;
            const isPeriodValid = examen.periode_active && !examen.periode_cloture;

            document.querySelectorAll('.note-input').forEach(input => {
                input.disabled = !(isDateValid && isPeriodValid);
            });
        } catch (error) {
            console.error("Erreur de validation de l'examen:", error);
        }
    }

    // Événements
    [classeSelect, matiereSelect, examenSelect].forEach(select => {
        select.addEventListener('change', () => {
            validateExam();
            loadStudents();
        });
    });

    // Chargement initial
    loadStudents();
});