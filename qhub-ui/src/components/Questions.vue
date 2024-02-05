<template>
  <v-container class="fill-height">
    <v-responsive class="text-center fill-height">
      <h1>Question Hub</h1>

      <v-btn @click="showFormDialog" class="ma-3">New Question</v-btn>

      <v-dialog v-model="formDialogVisible" max-width="600px">
        <v-card>
          <v-card-title>
            Add New Question
          </v-card-title>
          <v-card-text>
            <!-- Form fields -->
            <v-text-field v-model="title" label="Title"></v-text-field>
            <v-textarea v-model="message" label="Message"></v-textarea>
          </v-card-text>
          <v-card-actions>
            <!-- Buttons to submit or cancel the form -->
            <v-btn @click="addQuestion">Add</v-btn>
            <v-btn @click="closeFormDialog">Cancel</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <div>
        <v-expansion-panels class="mb-6">

          <v-expansion-panel v-for="question in questions" :key="question">

            <div class="d-flex">

              <div class="d-flex flex-column pt-2">
                <h3>{{ question.order }}</h3>
                <v-btn class="ma-1" size="small" variant="text" icon="mdi-thumb-up" color="blue-lighten-2"
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
const flaskIP = ref('http://localhost:5000/api')
const formDialogVisible = ref(false);
const title = ref('');
const message = ref('');

const fetchData = async () => {
  try {
    const response = await fetch(`${flaskIP.value}/get`);
    const result = await response.json();
    // Update questions on creation of componenet
    questions.value = result.sort((a, b) => b.order - a.order);
  } catch (error) {
    console.error('Error fetching data:', error);
  }
};

const voteUp = async (questionId) => {
  try {
    const response = await fetch(`${flaskIP.value}/vote_up`, {
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

const showFormDialog = () => {
  // Show the form dialog
  formDialogVisible.value = true;
};

const addQuestion = async () => {
  try {
    // Create the request body
    const requestBody = {
      title: title.value,
      message: message.value,
    };

    // Send a POST request to the server using fetch
    const response = await fetch(`${flaskIP.value}/add_question`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    // Check if the request was successful
    if (response.ok) {
      // You can optionally handle the response data here
      console.log('Question Added Successfully');
      // After successfully adding the question, get the updated questions and close the form dialog
      await fetchData();
      closeFormDialog();
    } else {
      // Handle errors if the request was not successful
      console.error('Error:', response.statusText);
    }
  } catch (error) {
    console.error('Error:', error.message);
  }
};

const closeFormDialog = () => {
  // Show the form dialog
  title.value = '';
  message.value = '';
  formDialogVisible.value = false;
};

onMounted(() => {
  fetchData();
});

</script>
