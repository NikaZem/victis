// Функция для добавления класса "show" к flash-сообщениям
function showFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(message => {
        message.classList.add('show');
        setTimeout(() => {
            message.classList.remove('show');
        }, 3000); // Убираем сообщение через 3 секунды
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const completeForms = document.querySelectorAll('.complete-form');
    completeForms.forEach(form => {
        form.addEventListener('submit', event => {
            event.preventDefault();
            const url = form.action;

            fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                if (response.ok) {
                    return response.json();
                } else {
                    throw new Error('Ошибка при обновлении привычки');
                }
            }).then(data => {
                const habitId = data.habit_id;
                const img = document.querySelector(`#chart-${habitId} img`);
                if (img) {
                    img.src = `/progress_chart/${habitId}?t=${Date.now()}`;
                }
                const progressElement = document.querySelector(`#habit-${habitId} .progress`);
                const daysLeftElement = document.querySelector(`#habit-${habitId} .days-left`);
                const motivationElement = document.querySelector(`#chart-${habitId} p`);

                if (progressElement) {
                    progressElement.textContent = `Прогресс: ${data.completed_days} дней`;
                }
                if (daysLeftElement) {
                    daysLeftElement.textContent = `Осталось: ${data.days_left} дней`;
                }
                if (motivationElement) {
                    motivationElement.textContent = data.motivation;
                }

                if (data.is_goal_reached) {
                    const formElement = document.querySelector(`#habit-${habitId} .complete-form`);
                    if (formElement) {
                        formElement.remove();
                    }
                }
            }).catch(error => {
                console.error('Ошибка:', error);
            });
        });
    });
});



// Вызываем функцию при загрузке страницы
document.addEventListener('DOMContentLoaded', showFlashMessages);

function updateChart(habitId, completedDays, targetDays, motivation) {
    const chartElement = document.querySelector(`#chart-${habitId}`);
    if (chartElement) {
        const img = chartElement.querySelector('img');
        img.src = `/progress_chart/${habitId}?t=${Date.now()}`;  // Добавляем параметр времени для обновления кэша
        const motivationText = chartElement.querySelector('p');
        motivationText.textContent = motivation;
    }
}


function markHabitComplete(habitId) {
    fetch(`/complete/${habitId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    }).then(response => response.json())
      .then(data => {
          if (data.is_goal_reached) {
              alert('Привычка завершена!');
          }
          updateChart(data.habit_id, data.completed_days, data.target_days, data.motivation);
      });
}

function deleteCompletedChart(habitId) {
    fetch(`/delete_chart/${habitId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    }).then(response => response.json())
      .then(data => {
          if (data.success) {
              document.querySelector(`#chart-completed-${habitId}`).remove();
          }
      }).catch(error => {
          console.error('Ошибка удаления диаграммы:', error);
      });
}


