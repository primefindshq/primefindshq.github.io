// All the bot's wording in one place. Edit freely.
// {placeholders} are filled in by logic.js. Each list is picked at random,
// so replies don't repeat and don't look like copy-paste spam.

export const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

export const T = {
  // Public reply under the comment, after the DM was sent
  publicReplySent: [
    "שלחנו לך בפרטי 📩",
    "נשלח! תבדקו את ההודעות 📬",
    "בדרך אליך בהודעה 🙌",
    "שלחתי לך את הקישור בפרטי 😉",
    "יש לך הודעה מאיתנו 📩",
    "הקישור מחכה לך בהודעות 👀",
    "צ'קו את הפרטי 📲",
    "שלחנו! תציצו בהודעות 🙂",
    "הקישור אצלך בפרטי 🔗",
    "זרקנו לך הודעה 📩",
  ],

  // Public reply when the DM could not be sent (e.g. the person's messages are closed)
  publicReplyBio: [
    "הקישור בביו 👆 שם הסרטון הזה מופיע ראשון",
    "לא הצלחנו לשלוח בפרטי, הקישור מחכה בביו 👆",
    "יש קישור בביו 👆",
  ],

  // DM sent after a comment on a reel we recognised (by the code word in the caption)
  dmVideo: [
    "היי! הנה הקישור מהסרטון \"{title}\" 👇\n{url}\n\nהמחירים בדולרים לפי אמזון ארה\"ב. לפני הזמנה כדאי לבדוק שהמוצר נשלח לישראל.",
    "בבקשה 🙌 כל מה שהופיע ב\"{title}\":\n{url}\n\nלפני שמזמינים, שווה לוודא שיש משלוח לישראל.",
    "תודה על התגובה! 😊 הקישור למה שראית בסרטון:\n{url}\n\nהמחיר בדולרים, לפני משלוח ומיסים.",
    "הנה זה 👇 \"{title}\"\n{url}\n\nטיפ: לפני הזמנה תבדקו בעמוד באמזון שיש משלוח לישראל.",
    "היי 👋 ביקשת או לא ביקשת, הנה הקישור מהסרטון:\n{url}\n\nהמחירים בדולרים לפי אמזון ארה\"ב.",
  ],

  // DM after a comment on a reel without a code word in the caption
  dmGeneric: [
    "היי! כל הסרטונים שלנו עם הקישורים נמצאים כאן 👇\n{index}\n\nהאחרון שעלה: \"{newestTitle}\"\n{newestUrl}",
    "תודה על התגובה! 😊 כל המוצרים מהסרטונים שלנו:\n{index}",
  ],
};
