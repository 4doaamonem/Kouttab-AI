// const { classifyText, isHealthy } = require("./aiClient");

// (async () => {
//   console.log("healthy:", await isHealthy());
//   console.log(await classifyText("أنا جربت أعوض بـ x باربعة وطلع الطرفين متساويين."));
// })();



// const { transcribeAudio, isHealthy } = require("./aiClient");
 
// (async () => {
//   console.log("healthy:", await isHealthy());
//   const file = process.argv[2];
//   if (!file) return console.log("usage: node test_transcribe.js <audio file>");
//   console.log(await transcribeAudio(file));
//   console.log()
// })();


const { checkRecitation, isHealthy } = require("./aiClient");

(async () => {
  console.log("healthy:", await isHealthy());
  const [file, ayah] = process.argv.slice(2);
  if (!file || !ayah) return console.log("usage: node test.js <audio file> <ayah, e.g. 1:1>");
  const result = await checkRecitation(file, ayah);
  console.log("transcription:", result.transcription);
  console.log(result.summary);
  console.log(result.words.filter((w) => w.status !== "ok"));
})();

// run this command after run ai_service: node test.js test2.wav 2:2

//front side

// COLORS = {"ok": "green", "tashkeel_error": "orange",
//           "word_error": "red", "missing": "gray", "extra": "purple"}

// def render_html(result):
//     parts = []
//     for w in result["words"]:
//         text = w["expected"] or w["got"]
//         parts.append(f'<span style="color:{COLORS[w["status"]]}">{text}</span>')
//     return " ".join(parts)