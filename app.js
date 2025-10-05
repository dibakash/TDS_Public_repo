const URL = "https://tds-public-repo.vercel.app/api/latency/test"
const userInputValue = document.querySelector("#id")
const form = document.querySelector("#apiForm")
const responseDiv = document.querySelector("#response")



form.addEventListener("submit", async (event) => {
    event.preventDefault(); // Prevent form from submitting traditionally

    const userInput = document.querySelector("#user").value;

    if (!userInput) {
        displayResponse("Please enter a user value");
        return;
    }

    try {
        const data = await fetchData(userInput);
        displayResponse(JSON.stringify(data, null, 2));
    } catch (error) {
        displayResponse(`Error: ${error.message}`);
    }
})

const fetchData = async (user) => {
    try {
        const response = await fetch(URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ user: user })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        throw new Error(`Failed to fetch data: ${error.message}`);
    }
}

const displayResponse = (message) => {
    responseDiv.innerHTML = `<pre>${message}</pre>`;
}