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
              <v-btn class="ma-1" size="small" variant="text" icon="mdi-thumb-up" color="blue-lighten-2"></v-btn>
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
import { ref } from 'vue'

const questions = ref(
  [
    { title: 'Python3 Issues', message: 'I cant run python3 commands on shell', order: 0 },
    { title: 'Python2 Issues', message: 'I cant run python3 commands on shell', order: 0 },
    { title: 'Python1 Issues', message: 'I cant run python3 commands on shell', order: 0 },
    { title: 'Python0 Issues', message: 'I cant run python3 commands on shell', order: 0 },
  ])

</script>
