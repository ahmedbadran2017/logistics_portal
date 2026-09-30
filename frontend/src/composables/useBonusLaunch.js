import { ref } from "vue";

// One shared switch so the launch notice can be reopened from anywhere (the
// Bonus page's "Rules" button) after it has been acknowledged. The component
// mounted in App.vue is the only thing that renders it.
const reopen = ref(0);

export function useBonusLaunch() {
  return {
    reopen,
    openRules: () => { reopen.value += 1; },
  };
}
