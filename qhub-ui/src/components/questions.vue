<template>
  <v-container class="fill-height">
    <v-responsive class="text-center fill-height">
      <h1>Question Hub</h1>

      <div>
        <v-expansion-panels class="mb-6">

          <v-expansion-panel v-for="question in questions" :key="question">

            <div class="d-flex">

              <div class="d-flex flex-column pt-2">
                <h3>{{ question.order }}</h3>
                <v-btn class="ma-1" size="small" 
                variant="text" icon="mdi-thumb-up" 
                color="blue-lighten-2"
                @click="voteUp(question.id)"></v-btn>
              </div>

              <v-expansion-panel-title expand-icon="mdi-menu-down">
                {{ question.title }}
              </v-expansion-panel-title>

            </div>


            <v-expansion-panel-text>
              {{ question.message }}
            </v-expansion-panel-text>

          </v-expansion-panel>

        </v-expansion-panels>
      </div>


    </v-responsive>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const questions = ref([])
const flaskIP = ''

const fetchData = async () => {
  try {
    const response = await fetch('http://localhost:5000/api/get');
    const result = await response.json();
    // Update questions on creation of componenet
    questions.value = result.sort((a, b) => b.order - a.order);
  } catch (error) {
    console.error('Error fetching data:', error);
  }
};

const voteUp = async (questionId) => {
      try {
        const response = await fetch('http://localhost:5000/api/vote_up', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            id: questionId,
          }),
        });

        const result = await response.json();

        if (result.success) {
          console.log('Order updated successfully');
          // re-fetch the data after updating the order
          fetchData();
        } else {
          console.error('Error updating order:', result.message);
        }
      } catch (error) {
        console.error('Error updating order:', error);
      }
    };


onMounted(() => {
  fetchData();
});

</script>
