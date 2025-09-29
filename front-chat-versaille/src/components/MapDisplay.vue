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
      <p>Route data is not available to display the map.</p>
    </div>
  </div>
</template>

<script>
import { computed } from "vue";

export default {
  name: "MapDisplay",
  props: {
    // Expect the full JSON object as a prop
    routeData: {
      type: Object,
      required: true,
    },
  },
  setup(props) {
    // Retrieve the Google Maps API key from environment variables
    const googleApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

    // A computed property to generate the iframe URL dynamically
    const mapUrl = computed(() => {
      // Ensure the route data is valid before processing
      if (
        !googleApiKey ||
        !props.routeData?.routes?.[0]?.legs?.[0]?.steps?.length
      ) {
        console.error(
          "Google Maps API key is missing or route data is invalid."
        );
        return "";
      }

      const steps = props.routeData.routes[0].legs[0].steps;

      // Extract the start location from the very first step
      const origin = steps[0].startLocation.latLng;
      // Extract the end location from the very last step
      const destination = steps[steps.length - 1].endLocation.latLng;

      const originString = `${origin.latitude},${origin.longitude}`;
      const destinationString = `${destination.latitude},${destination.longitude}`;

      // Construct the URL for the Google Maps Embed API (Directions mode)
      // The travel mode is set to 'walking' based on the JSON data.
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
  height: 100%;
  background-color: #e0e0e0; /* A light grey placeholder background */
  display: flex;
  justify-content: center;
  align-items: center;
}

.placeholder {
  font-family: "Source Serif Pro", serif;
  color: #555;
}
</style>
