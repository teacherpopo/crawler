import requests
import re
from bs4 import BeautifulSoup
import mysqlconnect
from multiprocessing import Process, JoinableQueue, Queue, Manager, Lock, current_process
import sys

def get_unique_words():
    database = 'test'
    with mysqlconnect.MysqlConnectionManager() as connection:
        cursor = connection.cursor()
        cursor.execute('use %s'%database)
        cursor.execute('select distinct binary word from collins')
        with open('wordlist_unique.txt','w') as f:
            for word, in cursor:
                f.write(word+'\n')
                
def html_parser(html_queue,lock):
    count = 0
    while True:       
        html = html_queue.get()
        if (html == None):
            html_queue.task_done()
            return
        count+=1
        soup = BeautifulSoup(html,'html.parser')
        
        #span.class.title, em.class.additional_spell_phontic, span.class.star_star*, span.class.via_rank, span.class_additional_pattern
        try:
            header = soup.find('div',id='collinsResult').h4
        except:
            with lock:
                print 'not found'
        else:
            obtained_word = unicode(header.find('span',class_='title').string)
            obtained_word = re.sub(ur'\u02cc|\u02c8','',obtained_word)
            '''if (obtained_word in unique_words):
                with lock:
                    print word,'duplicate:',obtained_word
            else:'''
            if (True):                                                
                #header information
                phonetic = header.find('em',class_='phonetic')               
                if (phonetic == None): phonetic = ''
                else: phonetic = unicode(phonetic.string)
                
                star = header.find('span',class_='star')
                if (star == None): star = 0
                else: star = int(star['class'][1][-1])
                
                vocabulary = header.find('span',class_='via')
                if (vocabulary == None): vocabulary = ''
                else: vocabulary = unicode(vocabulary.string)
    
                inflectives = header.find('span',class_='pattern')
                if (inflectives == None): inflectives = ''
                else: inflectives = re.sub('\n|(\t)+|( )+',' ',inflectives.string)
                
                #Each meaning of the word
                entry_list = soup('div',class_='collinsMajorTrans') # span.class_collinsOrder
                if (entry_list == []):
                    word = unicode(header.find_next_sibling('a').string)
                for entry in entry_list:
                    index = unicode(entry.find('span',class_='collinsOrder').string).split('.')[0]
                    explanation = entry.p.get_text(' ', strip=True) #span.class.additional p.get_text(' ',strip=True)
                    word_type = entry.find('span',class_='additional')
                    if (word_type == None): word_type=''
                    else: word_type = unicode(word_type.string)
                    explanation = re.sub('\n|(\t)+|( )+',' ',explanation)
                    explanation = explanation+'\n'
                    
                    #Each example sentence
                    example_list = ''
                    for example in entry.find_next_siblings(class_='exampleLists'):
                        example = example.div.get_text('\n',strip=True) # example.div(class_='examples')(p)
                        example_list+=example+'\n\n'
        html_queue.task_done()
        with lock:
            print count, 'th word parsed by the' ,current_process().name, 'th parser'
            sys.stdout.flush()

def get_html(html_queue,lock):
    session = requests.Session()
    query_url = 'http://dict.youdao.com/w/%s'
    with open('wordlist_20000.txt','r') as f:
            count=0
            for word in f:
                count+=1
                if (count==100): return
                word = word[:-1]
                try:
                    response = session.get(query_url%word)
                except requests.ConnectionError, e:
                    with lock:
                        print e
                    continue
                else:
                    html_queue.put(response.text)
                with lock:
                    print count, 'th word queried'
                    sys.stdout.flush()
    
if __name__ == "__main__":
    unique_words = set()

    with open('wordlist_unique.txt','r') as f:
        for word in f:
            unique_words.add(word[:-1])
            
    lock = Lock()
    html_queue = JoinableQueue()
    nparse = 3
    parse_jobs = []
    request_process = Process(target = get_html,args=(html_queue,lock))
    for i in range(nparse):
        parse_jobs.append(Process(target = html_parser, name=str(i), args=(html_queue,lock)))
    request_process.start()
    for i in range(nparse):
        parse_jobs[i].start()
    request_process.join()
    for i in range(nparse):
        html_queue.put(None)
    for i in range(nparse):
        parse_jobs[i].join()  
    html_queue.join()

    '''               
    cursor.execute('insert into collins values (%s,%s,%s,%s,%s,%s,%s,%s,%s)',
    (spelling, phonetic, star, inflectives, vocabulary, index, word_type, explanation, example_list))
    if(count%100==0): connection.commit()'''
        