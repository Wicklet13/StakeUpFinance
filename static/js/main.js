function transfer(token) {
    button = document.getElementById('transact-btn')
    button.disabled = true;
    button.value = "Processing...";

    $.ajax({
        url: '/transfer-post/'+token,
        data: $('form').serialize(),
        type: 'POST',
        success: function(response){
            response = JSON.parse(response);
            if(response['error'] == true){
                setErrorMsg(response['msg'], button, 'Transfer')
            } else {
                location.href = '/wallet'
            }
        },
        error: function(error){
            console.log("F"+error);
        }
    });
}

function addChild() {
    button = document.getElementById('add-child-btn')
    button.disabled = true;
    button.value = "Adding...";

    $.ajax({
        url: '/manage-account/add-child',
        data: $('form').serialize(),
        type: 'POST',
        success: function(response){
            response = JSON.parse(response);
            if(response['error'] == true){
                setErrorMsg(response['msg'], document.getElementById('show-add-child-button'), 'Add Child')
            } else {
                location.href = "/manage-account"
            }
        },
        error: function(error){
            console.log(error);
        }
    });
}

function addParent() {
    button = document.getElementById('add-parent-btn')
    button.disabled = true;
    button.value = "Adding...";


    $.ajax({
        url: '/manage-account/add-parent',
        data: $('form').serialize(),
        type: 'POST',
        success: function(response){
            response = JSON.parse(response);
            if(response['error'] == true){
                setErrorMsg(response['msg'], document.getElementById('show-add-parent-button'), 'Add Parent')
            } else {
                location.href = "/manage-account"
            }
        },
        error: function(error){
            console.log(error);
        }
    });
}

function setAddress(button) {
    $.ajax({
        url: '/transfer-post/get-address?id='+button.value,
        data: {},
        type: 'POST',
        success: function(response){
            response = JSON.parse(response);
            document.getElementById('to_address').value = response['address'];
        },
        error: function(error){
            console.log(error);
        }
    });
}

function setErrorMsg(msg, button=undefined, buttonVal="") {
    errorMsg = document.getElementById('errorMsg')
    errorMsg.innerHTML = msg
    errorMsg.hidden = false
    if(button) {
        button.disabled = false
        button.value=buttonVal
    }
}