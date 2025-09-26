document.addEventListener('DOMContentLoaded', () => {
    const navList = document.getElementById('nav-list');
    const content = document.getElementById('content');
    const quizSidebar = document.getElementById('quiz-sidebar');

    let courseData = null;

    fetch('data.json')
        .then(response => response.json())
        .then(data => {
            courseData = data;
            renderNav(data.chapters);
            renderChapter(0);
        });

    function renderNav(chapters) {
        navList.innerHTML = '';
        chapters.forEach((chapter, index) => {
            const li = document.createElement('li');
            li.className = 'nav-item';
            li.dataset.chapterIndex = index;
            li.innerHTML = `
                <div class="nav-item-radio"></div>
                <a class="nav-link">${chapter.chapter_title}</a>
            `;
            navList.appendChild(li);
        });
        updateActiveNavLink(0);
    }

    function renderChapter(index) {
        const chapter = courseData.chapters[index];
        content.innerHTML = '';

        const title = document.createElement('h2');
        title.textContent = chapter.chapter_title;
        content.appendChild(title);

        if (chapter.content) {
            chapter.content.forEach(item => {
                const pContainer = document.createElement('div');
                pContainer.className = 'paragraph-grid';

                const textContent = document.createElement('div');
                textContent.className = 'paragraph-text-content';
                textContent.innerHTML = marked.parse(item.paragraph);
                pContainer.appendChild(textContent);

                const quizContainer = document.createElement('div');
                quizContainer.className = 'paragraph-quiz-icon-container';
                if (item.quiz_insertable && item.quiz) {
                    const button = document.createElement('button');
                    button.className = 'quiz-button';
                    button.innerHTML = `<img src="learnyourway.withgoogle.com/learnyourway.withgoogle.com/static/immersive-text/spark_info_2.svg" alt="Show Quiz"/>`;
                    button.title = 'Show Quiz';
                    button.dataset.quiz = JSON.stringify(item.quiz);
                    quizContainer.appendChild(button);
                }
                pContainer.appendChild(quizContainer);

                if (item.images && item.images.length > 0) {
                    const imageContainer = document.createElement('div');
                    imageContainer.className = 'paragraph-image-container';
                    item.images.forEach(imgData => {
                        const img = document.createElement('img');
                        img.src = imgData.url;
                        img.className = 'img-responsive';
                        imageContainer.appendChild(img);
                    });
                    pContainer.appendChild(imageContainer);
                }
                content.appendChild(pContainer);
            });
        }

        content.querySelectorAll('.quiz-button').forEach(button => {
            button.addEventListener('click', (e) => {
                const quizData = JSON.parse(e.currentTarget.dataset.quiz);
                showQuizInSidebar(quizData);
            });
        });

        const ke = chapter.knowledge_extension;
        if (ke && ke.paragraphs && ke.paragraphs.length > 0) {
            const module = document.createElement('div');
            module.className = 'core-ideas-module';
            module.innerHTML = `<div class="module-header"><h4>Core ideas illustrated by AI</h4></div>`;
            const moduleContent = document.createElement('div');
            ke.paragraphs.forEach(p => {
                const row = document.createElement('div');
                row.className = 'ke-row';
                row.style.display = 'flex';
                row.style.alignItems = 'center';
                row.style.gap = '20px';

                const textDiv = document.createElement('div');
                textDiv.className = 'ke-text';
                textDiv.style.flex = '1';
                textDiv.innerHTML = marked.parse(p.content);
                row.appendChild(textDiv);
                
                if (p.image) {
                    const imageDiv = document.createElement('div');
                    imageDiv.className = 'ke-image';
                    imageDiv.style.flexShrink = '0';
                    imageDiv.style.width = '300px';
                    imageDiv.style.height = '400px';
                    
                    const img = document.createElement('img');
                    img.src = p.image;
                    img.alt = 'Illustration';
                    img.style.width = '100%';
                    img.style.height = '100%';
                    img.style.objectFit = 'contain';
                    img.style.borderRadius = '8px';
                    
                    imageDiv.appendChild(img);
                    row.appendChild(imageDiv);
                }
                
                moduleContent.appendChild(row);
            });
            module.appendChild(moduleContent);
            content.appendChild(module);
        }

        if (chapter.chapter_quiz) {
            const module = document.createElement('div');
            module.className = 'content-module';
            new InteractiveQuiz(chapter.chapter_quiz, module);
            content.appendChild(module);
        }

        if (parseInt(index) === courseData.chapters.length - 1 && courseData.comprehensive_quiz) {
            const module = document.createElement('div');
            module.className = 'content-module';
            new InteractiveQuiz(courseData.comprehensive_quiz, module);
            content.appendChild(module);
        }

        updateActiveNavLink(index);
    }

    function showQuizInSidebar(quizData) {
        quizSidebar.innerHTML = '';
        new InteractiveQuiz(quizData, quizSidebar, () => quizSidebar.classList.remove('show'));
        quizSidebar.classList.add('show');
    }

    class InteractiveQuiz {
        constructor(quizData, container, closeCallback) {
            this.container = container;
            this.questions = this.flattenQuestions(quizData);
            this.currentIndex = 0;
            this.closeCallback = closeCallback;
            if (this.questions.length > 0) {
                this.render();
            }
        }

        flattenQuestions(data) {
            let all = [];
            if (data.multiple_choice) all.push(...data.multiple_choice.map(q => ({...q, type: 'mcq'})));
            if (data.fill_in_the_blank) all.push(...data.fill_in_the_blank.map(q => ({...q, type: 'fib'})));
            if (data.true_false) all.push(...data.true_false.map(q => ({...q, type: 'tf'})));
            if (data.short_answer) all.push(...data.short_answer.map(q => ({...q, type: 'sa'})));
            return all;
        }

        render() {
            this.container.innerHTML = `
                <div class="quiz-content-container">
                    ${this.closeCallback ? '<button class="close-quiz-btn">&times;</button>' : ''}
                    <div class="quiz-question-container"></div>
                    <div class="quiz-feedback"></div>
                    <div class="quiz-navigation">
                        <button class="quiz-nav-btn prev-btn">Prev</button>
                        <div class="quiz-actions"></div>
                        <button class="quiz-nav-btn next-btn">Next</button>
                    </div>
                </div>
            `;
            this.questionContainer = this.container.querySelector('.quiz-question-container');
            this.feedbackContainer = this.container.querySelector('.quiz-feedback');
            this.actionsContainer = this.container.querySelector('.quiz-actions');
            if (this.closeCallback) {
                this.container.querySelector('.close-quiz-btn').addEventListener('click', this.closeCallback);
            }
            this.container.querySelector('.prev-btn').addEventListener('click', () => this.navigate(-1));
            this.container.querySelector('.next-btn').addEventListener('click', () => this.navigate(1));
            this.renderQuestion();
        }

        renderQuestion() {
            const question = this.questions[this.currentIndex];
            this.questionContainer.innerHTML = '';
            this.feedbackContainer.style.display = 'none';
            this.actionsContainer.innerHTML = '';
            this.questionContainer.innerHTML = `<p><strong>${question.question}</strong></p>`;
            const answerContainer = document.createElement('div');
            answerContainer.className = 'quiz-options';

            let selectedOption = null;

            const check = (isCorrect) => {
                this.feedbackContainer.style.display = 'block';
                this.feedbackContainer.className = `quiz-feedback ${isCorrect ? 'correct' : 'incorrect'}`;
                // this.feedbackContainer.textContent = isCorrect ? 'Correct!' : `Incorrect. The correct answer is: ${question.correct_answer}`;
                
                // 为选择题和判断题添加颜色反馈
                if (question.type === 'mcq' || question.type === 'tf') {
                    // 找到所有选项按钮
                    const optionButtons = this.questionContainer.querySelectorAll('.quiz-option-btn');
                    
                    optionButtons.forEach(btn => {
                        // 如果是正确答案，添加绿色样式
                        if (btn.textContent === question.correct_answer) {
                            btn.style.backgroundColor = '#C5E6C7';
                            // btn.style.color = 'white';
                            btn.style.color = '#333';

                            btn.style.border = '2px solid #C5E6C7';
                        }
                        // 如果是用户选择的错误答案，添加红色样式
                        else if (selectedOption && btn === selectedOption && !isCorrect) {
                            btn.style.backgroundColor = '#ffd6cc';
                            btn.style.color = '#333';
                            btn.style.border = '2px solid #ffd6cc';
                        }
                    });
                }
                
                this.questionContainer.querySelectorAll('button, input, textarea').forEach(el => el.disabled = true);
                this.actionsContainer.innerHTML = '';
            };

            switch (question.type) {
                case 'mcq':
                case 'tf':
                    const options = question.type === 'tf' ? ['True', 'False'] : question.options;
                    options.forEach(option => {
                        const button = document.createElement('button');
                        button.className = 'quiz-option-btn';
                        button.textContent = option;
                        button.onclick = () => {
                            selectedOption = button;
                            this.questionContainer.querySelectorAll('.quiz-option-btn').forEach(btn => btn.classList.remove('selected'));
                            button.classList.add('selected');
                        };
                        answerContainer.appendChild(button);
                    });

                    const checkBtn = document.createElement('button');
                    checkBtn.className = 'check-quiz-btn';
                    checkBtn.textContent = 'Check';
                    checkBtn.onclick = () => {
                        if (selectedOption) {
                            const isCorrect = question.type === 'tf' ? 
                                (String(selectedOption.textContent === 'True') == String(question.correct_answer)) :
                                (selectedOption.textContent === question.correct_answer);
                            check(isCorrect);
                        }
                    };
                    this.actionsContainer.appendChild(checkBtn);
                    break;
                default: // fib & sa
                    const input = document.createElement(question.type === 'sa' ? 'textarea' : 'input');
                    input.className = 'form-control';
                    const submitBtn = document.createElement('button');
                    submitBtn.className = 'check-quiz-btn';
                    submitBtn.textContent = 'Submit';
                    submitBtn.onclick = () => check(input.value.trim().toLowerCase() === question.correct_answer.toLowerCase());
                    answerContainer.appendChild(input);
                    this.actionsContainer.appendChild(submitBtn);
                    break;
            }
            this.questionContainer.appendChild(answerContainer);
            this.updateNavButtons();
        }

        navigate(direction) {
            const newIndex = this.currentIndex + direction;
            if (newIndex >= 0 && newIndex < this.questions.length) {
                this.currentIndex = newIndex;
                this.render();
            }
        }

        updateNavButtons() {
            this.container.querySelector('.prev-btn').disabled = this.currentIndex === 0;
            this.container.querySelector('.next-btn').disabled = this.currentIndex === this.questions.length - 1;
        }
    }

    function updateActiveNavLink(index) {
        document.querySelectorAll('#nav-list .nav-item').forEach((item, i) => {
            item.classList.toggle('active', parseInt(i) === parseInt(index));
        });
    }

    navList.addEventListener('click', (e) => {
        const navItem = e.target.closest('.nav-item');
        if (navItem) {
            e.preventDefault();
            renderChapter(navItem.dataset.chapterIndex);
        }
    });
    
    // 文件上传功能
    const uploadButton = document.getElementById('upload-button');
    const fileInput = document.getElementById('file-input');
    const uploadStatus = document.getElementById('upload-status');
    const statusText = document.getElementById('status-text');
    
    uploadButton.addEventListener('click', () => {
        fileInput.click();
    });
    
    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        // 检查文件类型
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showStatus('Only PDF files are supported', 'error');
            return;
        }
        
        // 显示上传状态
        showStatus('Working on your upload...', 'uploading');
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                if (result.status === 'success') {
                    showStatus('upload success', 'processing');

                    location.replace(location.pathname + '?t=' + Date.now());
                } else {
                    showStatus(result.message || 'upload failed', 'error');
                }
            } else {
                const errorResult = await response.json();
                showStatus(errorResult.message || 'upload failed', 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            showStatus('upload failed：network error', 'error');
        }
        
        // 清空文件输入
        fileInput.value = '';
    });
    
    function showStatus(message, type) {
        statusText.textContent = message;
        uploadStatus.className = 'upload-status';
        
        if (type === 'success') {
            uploadStatus.classList.add('success');
        } else if (type === 'error') {
            uploadStatus.classList.add('error');
        }
        
        uploadStatus.style.display = 'flex';
        
        // 如果是错误消息，5秒后自动隐藏
        if (type === 'error') {
            setTimeout(() => {
                uploadStatus.style.display = 'none';
            }, 5000);
        }
    }
});