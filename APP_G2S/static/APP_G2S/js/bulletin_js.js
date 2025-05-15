(function() {
    document.addEventListener('DOMContentLoaded', () => {
        const classeSelect = document.querySelector("#classe-select select");
        const elevesList = document.querySelector("#eleves-list");
        const selectedCount = document.querySelector("#selected-count");
        let selectedeleves = new Set();
        let currentClasseId = null;
        const searchInput = document.querySelector("#search-eleves");




        // Gestionnaire de sélection de classe
    classeSelect.addEventListener("change", async function() {
            currentClasseId = this.value;
            searchInput.value = ''; // Réinitialise la recherche
            try {
                showLoading(true);
                const response = await fetch(`/get_eleves_par_classe/?classe_id=${currentClasseId}`);
                if (!response.ok) throw new Error(`Erreur HTTP: ${response.status}`);
                const data = await response.json();
                updateelevesList(data);
            } catch (error) {
                showError(error.message);
            } finally {
                showLoading(false);
            }
        });

        // Mise à jour de la liste des élèves
        function updateelevesList(responseData) {
            elevesList.innerHTML = "";
            selectedeleves.clear();
            updateSelectedCount();

            if (!responseData?.eleves?.length) {
                showError("Aucun élève trouvé dans cette classe");
                return;
            }

            responseData.eleves.forEach(eleve => {
                const container = document.createElement("div");
                container.className = "eleve-item flex items-center p-2 hover:bg-gray-50";
                container.innerHTML = `
                    <input type="checkbox" class="eleve-checkbox mr-3" data-id="${eleve.id}">
                    <div class="flex-1 clickable-details">
                        ${eleve.nom} ${eleve.prenom}
                        <span class="float-right text-gray-500">${eleve.identifiant || ''}</span>
                    </div>
                `;
                elevesList.appendChild(container);
            });

            setupCheckboxHandlers();
            setupDetailsHandlers();









        }


        
            // Gestion de la recherche

            searchInput.addEventListener("input", function() {
                const searchTerm = this.value.trim().toLowerCase();
                const eleveItems = elevesList.querySelectorAll('.eleve-item');
                
                eleveItems.forEach(item => {
                    const textContent = item.querySelector('.clickable-details').textContent.toLowerCase();
                    item.style.display = textContent.includes(searchTerm) ? '' : 'none';
                });
            })

        // Gestion des checkboxes
        function setupCheckboxHandlers() {
            document.querySelectorAll(".eleve-checkbox").forEach(checkbox => {
                checkbox.addEventListener("change", function() {
                    const id = this.dataset.id;
                    const item = this.closest('.eleve-item');
                    
                    if (this.checked) {
                        selectedeleves.add(id);
                        item.classList.add('bg-blue-100');
                    } else {
                        selectedeleves.delete(id);
                        item.classList.remove('bg-blue-100');
                    }
                    updateSelectedCount();
                });
            });
        }

        // Gestion des clics pour afficher le bulletin
        function setupDetailsHandlers() {
            document.querySelectorAll(".clickable-details").forEach(div => {
                div.addEventListener("click", async function() {
                    const eleve_id = this.closest('.eleve-item').querySelector('.eleve-checkbox').dataset.id;
                    try {
                        showLoading(true);
                        showbulletin(false)
                        const response = await fetch(`/get_eleves_classe/?eleve_id=${eleve_id}&classe_id=${currentClasseId}`);
                        if (!response.ok) throw new Error(`Erreur HTTP: ${response.status}`);
                        const data = await response.json();
                            console.log(data)
                        updateBulletinPanel(data);
                    } catch (error) {
                        showError(error.message);
                    } finally {
                        showLoading(false);
                        showbulletin(true)
                        
                    }
                });
            });
        }

        function updateBulletinPanel(eleveData) {
            const tbody = document.querySelector("table tbody");
            const moyenneGeneraleCell = document.getElementById("moyenne-generale");

            console.log(tbody)
            
            // Vérifier que les données sont valides
            if (!eleveData?.eleves?.[0]?.notes?.length) {
                console.error("Données de notes invalides");
                return;
            }
        
            const eleve = eleveData.eleves[0];
            const notes = eleve.notes;
            

            document.getElementById('annees').textContent = 
                `${eleveData.periode}`
            // Mettre à jour le nom de l'élève
            document.getElementById('eleve-nom').textContent = 
                `${eleve.nom} ${eleve.prenom}`;
            
            document.getElementById('eleve-classe').textContent = 
                `${eleveData.classe}`;
            
            document.getElementById('eleve-contact').textContent = 
                `${eleve.telephone}`;
            
            document.getElementById('eleve-residence').textContent = 
                `${eleve.residence}`;
            
            // Supprimer les anciennes lignes de matières (sauf la ligne template et les totaux)
            let d = document.querySelectorAll("tr[data-matiere]:not([data-template])").forEach(row => row.remove());
            console.log(d)
            // Insérer les nouvelles lignes de matières
            notes.forEach(note => {
                const row = document.createElement("tr");
                row.className = "hover:bg-gray-50";
                row.setAttribute("data-matiere", note.matiere_id);
                console.log(note.matiere_id)
                console.log(note.matiere_nom)
                console.log(note.classe_note)
                row.innerHTML = `
                    <td class="border-2 border-gray-300 p-3">${note.matiere_nom}</td>
                    <td class="border-2 border-gray-300 p-3 text-center coefficient">${note.coefficient}</td>
                    <!-- Note de classe -->
                    <td class="border-2 border-gray-300 p-3">
                        <input type="number"
                            readonly=true 
                            step="0.01" 
                            min="0" 
                            max="20" 
                            placeholder="0.00"
                            name="note_classe_${note.matiere_id}" 
                            class="w-full text-center border rounded py-1 px-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
                            value="${note.classe_note || '--'}">
                    </td>
                    <!-- Note d'examen -->
                    <td class="border-2 border-gray-300 p-3">
                        <input type="number" 
                            readonly=true
                            step="0.01" 
                            min="0" 
                            max="40" 
                            placeholder="0.00"
                            name="note_exam_${note.matiere_id}" 
                            class="w-full text-center border rounded py-1 px-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
                            value="${note.examen_note*2 || '--'}">
                    </td>
                    <!-- Moyenne coefficient -->
                    <td class="border-2 border-gray-300 p-3 text-center moyenne-coeff">
                        <input type="number" 
                            readonly=true
                            step="0.01" 
                            min="0" 
                            max="20" 
                            placeholder="0.00"
                            name="moyenne_coeff_${note.matiere_id}" 
                            class="w-full text-center border rounded py-1 px-2 focus:outline-none focus:ring-2 focus:ring-blue-200"
                            value="${note.moyenne_coefficient || '--'}">
                    </td>
                `;
                
                // Insérer avant la ligne de moyenne générale
                tbody.insertBefore(row, document.getElementById("tr"));
            });
            
            // Mettre à jour la moyenne générale
            if (eleve.moyenne_generale) {
                moyenneGeneraleCell.textContent = parseFloat(eleve.moyenne_generale).toFixed(2);
            } else {
                moyenneGeneraleCell.textContent = '--';
            }

                   // js d'appreciation 
            const moyenneGeneraleElement = document.getElementById('moyenne-generale');
            const appreciationElement = document.getElementById('appreciation-generale');

            function updateAppreciation() {
                const moyenne = parseFloat(moyenneGeneraleElement.textContent);
                let appreciation = '';

                if (!isNaN(moyenne)) {
                if (moyenne >= 16) {
                    appreciation = "Excellent travail, continuez ainsi.";
                } else if (moyenne >= 14) {
                    appreciation = "Très bon travail, vous êtes sur la bonne voie.";
                } else if (moyenne >= 12) {
                    appreciation = "Bon travail, mais il y a encore des points à améliorer.";
                } else if (moyenne >= 10) {
                    appreciation = "Travail passable, des efforts supplémentaires sont nécessaires.";
                } else {
                    appreciation = "Insuffisant, il faut travailler beaucoup plus.";
                }
                }

                appreciationElement.value = appreciation;
            }

            // Update appreciation when moyenne générale changes
            const observer = new MutationObserver(updateAppreciation);
            observer.observe(moyenneGeneraleElement, { childList: true });

            // Initial update
            updateAppreciation();
            
            
            // Afficher le panneau du bulletin
            showbulletin(true);














        }
        
        document.querySelector("#generate-selected").addEventListener("click", async () => {
            const selectedIds = Array.from(selectedeleves);
            
            if (selectedIds.length === 0) {
                showNotification('Veuillez sélectionner au moins un élève', 'red');
                return;
            }
        
            if (!confirm(`Générer ${selectedIds.length} bulletin(s) ?`)) return;
        
            try {
                showLoading(true);
                disableGenerateButton(true);
        
                const response = await fetch("/generate_bulletins/", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify({
                        eleve_ids: selectedIds,
                        classe_id: currentClasseId
                    })
                });
        
                const data = await response.json();

                console.log(data)
                
                if (data.success) {
                    showNotification(`${data.generated || data.updated} bulletin(s) générés avec succès !`, 'green');
                    refreshBulletinData();
                } else {
                    throw new Error(data.error || "Erreur lors de la génération");
                }
            } catch (error) {
                showNotification(error.message, 'red');
                console.error('Generation Error:', error);
            } finally {
                showLoading(false);
                disableGenerateButton(false);
            }
        });
        
        // Fonctions utilitaires
        function disableGenerateButton(disabled) {
            const btn = document.querySelector("#generate-selected");
            btn.disabled = disabled;
            btn.classList.toggle('opacity-50', disabled);
        }
        

        // Rafraîchir les données du bulletin après génération
        // Cette fonction désélectionne tous les élèves et met à jour le compteur
        function refreshBulletinData() {
            document.querySelectorAll(".eleve-checkbox:checked").forEach(checkbox => {
                checkbox.checked = false;
                selectedeleves.delete(checkbox.dataset.id);
                checkbox.closest('.eleve-item').classList.remove('bg-blue-100');
            });
            updateSelectedCount();
        }


 


        // Gestionnaires globaux
        // Sélectionner ou désélectionner tous les élèves
        document.querySelector("#select-all").addEventListener("click", () => {
            document.querySelectorAll(".eleve-checkbox").forEach(checkbox => {
                checkbox.checked = true;
                selectedeleves.add(checkbox.dataset.id);
                checkbox.closest('.eleve-item').classList.add('bg-blue-100');
            });
            updateSelectedCount();
        });

        document.querySelector("#deselect-all").addEventListener("click", () => {
            document.querySelectorAll(".eleve-checkbox").forEach(checkbox => {
                checkbox.checked = false;
                selectedeleves.delete(checkbox.dataset.id);
                checkbox.closest('.eleve-item').classList.remove('bg-blue-100');
            });
            updateSelectedCount();
        });



        // Mettre à jour le compteur d'élèves sélectionnés
        function updateSelectedCount() {
            selectedCount.textContent = selectedeleves.size;
        }









        // Afficher ou masquer le panneau de chargement

        function showLoading(show) {
            document.getElementById('loading-indicator').classList.toggle('hidden', !show);
        }

        // Afficher ou masquer le panneau de bulletin
        function showbulletin(show) {
            document.getElementById('Bulletin').classList.toggle('hidden', !show)
        }





        // Afficher un message d'erreur avec un panneau affiché 3 secondes

        function showNotification(message, color = 'blue') {
            const notification = document.createElement('div');
            notification.className = `fixed top-[100px] right-4 p-4 rounded-lg text-white bg-${color}-500 shadow-lg`;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => notification.remove(), 3000);
        }


        // function showError(message) {
        //     const existing = document.querySelector('.error-message');
        //     if (existing) existing.remove();
            
        //     const errorDiv = document.createElement("div");
        //     errorDiv.className = "error-message p-3 mb-4 text-red-800 bg-red-50 rounded";
        //     errorDiv.textContent = `Erreur : ${message}`;
        //     elevesList.parentElement.prepend(errorDiv);
        // }
    });
})();