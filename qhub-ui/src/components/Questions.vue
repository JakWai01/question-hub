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
            <v-text-field v-model="text" label="Title"></v-text-field>
          </v-card-text>
          <v-card-actions>
            <!-- Buttons to submit or cancel the form -->
            <v-btn @click="addQuestion">Add</v-btn>
            <v-btn @click="closeFormDialog">Cancel</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <div>
        <!-- Loop through the questions and display each one as a card -->
        <v-card v-for="question in questions" :key="question.uuid" class="mb-2">
          <v-card-title></v-card-title>
          <v-card-text>
            {{ question.text }}
          </v-card-text>
          <v-card-actions>
            <v-spacer></v-spacer>
            <!-- Like button -->
            <v-btn @click="voteUp(question.uuid)">
              <v-icon color="red-darken-3" size="large">mdi-heart</v-icon>
              <span class="text-subtitle-1">{{ question.votes }}</span>
            </v-btn>
          </v-card-actions>
        </v-card>
      </div>


    </v-responsive>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const questions = ref([])
const flaskIP = ref('/api')
const formDialogVisible = ref(false);
const text = ref('');

const fetchData = async () => {
  try {
    const response = await fetch(`${flaskIP.value}/get`);
    const result = await response.json();
    // Update questions on creation of componenet
    console.log(result)
    questions.value = result.sort((a, b) => b.votes - a.votes);
  } catch (error) {
    console.error('Error fetching data:', error);
  }
};

const voteUp = async (uuid) => {
  try {
    const response = await fetch(`${flaskIP.value}/vote_up`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        // TODO: QuestionID is null
        uuid: uuid,
      }),
    });

    const result = await response.json();

    if (result.success) {
      console.log('Order updated successfully');
      // re-fetch the data after updating the order
      await fetchData();
      closeFormDialog()
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
      text: text.value,
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
  text.value = '';
  formDialogVisible.value = false;
};

onMounted(() => {
  fetchData();
});

</script>
