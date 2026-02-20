document.addEventListener('DOMContentLoaded', function() {
    const warehouseSelect = document.getElementById('id_warehouse_select');
    const boxesSelect = document.getElementById('id_boxes_select');
    
    if (!warehouseSelect || !boxesSelect) return;

    function loadBoxes() {
        const warehouseId = warehouseSelect.value;
        
        if (!warehouseId) {
            boxesSelect.innerHTML = '<option value="">-- Сначала выберите склад --</option>';
            return;
        }

        const originalOptions = boxesSelect.innerHTML;
        boxesSelect.innerHTML = '<option value="">Загрузка...</option>';

        fetch(`/storage/ajax/get-boxes/?warehouse_id=${warehouseId}`)
            .then(response => response.json())
            .then(data => {
                boxesSelect.innerHTML = ''; // Очищаем текущие опции
                
                if (data.boxes.length === 0) {
                    boxesSelect.innerHTML = '<option value="">Нет доступных боксов на этом складе</option>';
                } else {
                    data.boxes.forEach(box => {
                        const option = document.createElement('option');
                        option.value = box.id;
                        option.textContent = box.label;
                        if (box.disabled) {
                            option.disabled = true;
                            option.textContent += " (Недоступен)";
                        }
                        boxesSelect.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error loading boxes:', error);
                boxesSelect.innerHTML = '<option value="">Ошибка загрузки списка</option>';
            });
    }

    warehouseSelect.addEventListener('change', loadBoxes);


});