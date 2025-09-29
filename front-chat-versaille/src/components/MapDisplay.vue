// src/components/MapDisplay.vue

<template>
  <div class="map-container">
    <iframe
      v-if="mapUrl"
      width="100%"
      height="100%"
      style="border: 0"
      loading="lazy"
      allowfullscreen
      :src="mapUrl"
    >
    </iframe>
    <div v-else class="placeholder">
      <p>Route data is not available or API key is missing.</p>
    </div>
  </div>
</template>

<script>
import { computed } from "vue";

export default {
  name: "MapDisplay",
  props: {
    routeData: {
      type: Object,
      required: true,
    },
    selectedLegIndex: {
      type: Number,
      required: true,
    },
  },
  setup(props) {
    const googleApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

    const mapUrl = computed(() => {
      const leg = props.routeData?.routes?.[0]?.legs?.[props.selectedLegIndex];

      if (!googleApiKey || !leg?.steps?.length) {
        console.error(
          "Google Maps API key is missing or the selected leg data is invalid."
        );
        return "";
      }

      const steps = leg.steps;

      // --- FIX START ---
      // Correctly access the nested latLng object using camelCase
      const origin = steps[0].startLocation.latLng;
      const destination = steps[steps.length - 1].endLocation.latLng;

      // Correctly access the latitude and longitude properties
      const originString = `${origin.latitude},${origin.longitude}`;
      const destinationString = `${destination.latitude},${destination.longitude}`;
      // --- FIX END ---

      return `https://www.google.com/maps/embed/v1/directions?key=${googleApiKey}&origin=${originString}&destination=${destinationString}&mode=walking`;
    });

    return {
      mapUrl,
    };
  },
};
</script>

<style scoped>
.map-container {
  width: 100%;
  /* Let flexbox handle the height */
  flex-grow: 1;
  background-color: #e0e0e0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.placeholder {
  font-family: "Source Serif Pro", serif;
  color: #555;
}
</style>
