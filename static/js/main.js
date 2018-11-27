        function showAlert(text){
            $('#alert').html('<div class="alert alert-danger alert-dismissible"><a href="#" class="close" data-dismiss="alert" aria-label="close">&times;</a><strong>Alert!</strong>  ' + text + '!</div>');
        }
        function validate(){
            if($('input[name=Reply_to]').val()===null ||$('input[name=Reply_to]').val()==="")
            {
                showAlert('Please insert Reply email address');
                return false;
            }
            // if ($('input[name=To]').val()===null|| $('input[name=To]').val()===""){
            //     showAlert('Please insert To email address');
            //     return false;
            // }
            if ($('input[name=subject]').val()===null|| $('input[name=subject]').val()===""){
                showAlert('Please insert Subject of Email');
                return false;
            }
            if ($('input[name=template]').val()==='' || $('input[name=template]').val()===null){
                showAlert('Please choose email template file');
                return false;
            }
            return true;
        }
        $.fn.fileUploader = function (filesToUpload, sectionIdentifier) {
            var fileIdCounter = 0;

            this.closest(".files").change(function (evt) {
                var output = [];
                var content = "";
                for (var i = 0; i < evt.target.files.length; i++) {
                    fileIdCounter++;
                    var file = evt.target.files[i];
                    var fileId = sectionIdentifier + fileIdCounter;

                    filesToUpload.push({
                        id: fileId,
                        file: file
                    });
                     var removeLink = "<a class=\"removeFile btn-circle\" href=\"#\" data-fileid=\"" + fileId + "\"><i class='fa fa-trash' aria-hidden='true'></i></a>";
                     output.push("<li><strong>", escape(file.name), "</strong> ", removeLink, "</li> ");
                };

                $(this).children(".fileList")
                    .append(output.join(""));
                //reset the input to null - nice little chrome bug!
                evt.target.value = null;
            });

            $(this).on("click", ".removeFile", function (e) {
                e.preventDefault();

                var fileId = $(this).parent().children("a").data("fileid");
                for (var i = 0; i < filesToUpload.length; ++i) {
                    if (filesToUpload[i].id === fileId)
                        filesToUpload.splice(i, 1);
                }
                $(this).parent().remove();
            });

            this.clear = function () {
                for (var i = 0; i < filesToUpload.length; ++i) {
                    if (filesToUpload[i].id.indexOf(sectionIdentifier) >= 0)
                        filesToUpload.splice(i, 1);
                }
                $(this).children(".fileList").empty();
            }
            return this;
        };

        (function () {
            var filesToUpload = [];
            var files1Uploader = $("#files1").fileUploader(filesToUpload, "attachFiles");

            $("input[type=submit]").click(function (e) {
                e.preventDefault();
                $('#alert').html('');
                if(validate()){
                        var formData = new FormData();
                        for (var i = 0, len = filesToUpload.length; i < len; i++) {
                            formData.append("attachFiles", filesToUpload[i].file);
                        }

                        var importFiles = $('input[name=template]')[0].files;
                        $.each( importFiles, function( index, value ) {
                            formData.append( 'template', value )
                        });

                        formData.append('msg[Reply_to]', $('input[name=Reply_to]').val());
                        formData.append('msg[To]', $('input[name=To]').val());
                        formData.append('subject', $('input[name=subject]').val());
                        formData.append('name', $('input[name=name]').val());
                        formData.append('address', $('input[name=address]').val());
                        formData.append('price', $('input[name=price]').val());
                        
                        $('#spinner').css('display', 'block');
                        $(this).prop('disabled', true);
                        $.ajax({
                            url: "/restApi",
                            data: formData,
                            processData: false,
                            contentType: false,
                            type: "POST",
                            success: function (data) {                                
                                $('#spinner').css('display', 'none');
                                $('#alert').html('');
                                files1Uploader.clear();
                                $("input[type=submit]").prop('disabled', false);
                                $("input[type=submit]").removeAttr('disabled');                                
                                alert("Successfully Sent!");
                            },
                            error: function (err) {
                                console.log(err);
                                $('#spinner').css('display', 'none');
                                $("input[type=submit]").prop('disabled', false);
                                $("input[type=submit]").removeAttr('disabled');
                            }
                        });
                    }
                });
        })()