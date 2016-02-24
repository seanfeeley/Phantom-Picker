import os
import urllib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2
import json
import random

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

MAIN_PAGE_FOOTER_TEMPLATE = """\
    <form action="/sign?%s" method="post">
      <div><textarea name="content" rows="3" cols="60"></textarea></div>
      <div><input type="submit" value="Sign Guestbook"></div>
    </form>
    <hr>
    <form>Guestbook name:
      <input value="%s" name="guestbook_name">
      <input type="submit" value="switch">
    </form>
    <a href="%s">%s</a>
  </body>
</html>
"""


def getAllPhantoms():
    phantoms = Phantom.query().fetch()
    if len(phantoms)==0:
        data=[]
        with open('ghosts.json') as data_file:    
            data = json.load(data_file)
        for d in data:

            p=Phantom(name=d["Ghost name"],description=d["Description"])

            p.put()
        phantoms = Phantom.query().fetch()
    return phantoms



class Phantom(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    name = ndb.StringProperty()
    description = ndb.StringProperty()
    def toDict(self):
        return {"name":self.name,"description":self.description}





class Person(ndb.Model):
    """Sub model for representing an author."""
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    phantom_name=ndb.StructuredProperty(Phantom)




class MainPage(webapp2.RequestHandler):

    def get(self):
        person_id = self.request.get('person_id')
        phantom_id = self.request.get('phantom_id')

        new_person=None
        if person_id and phantom_id:
            person=Person.get_by_id(int(person_id))
            phantom=Phantom.get_by_id(int(phantom_id))
           
            person.phantom_name=phantom
            person.put()
            new_person=person
   
        phantoms=getAllPhantoms()
        people=[]
        lonely_phantoms=[]
        for phantom in phantoms:
            possible_persons=Person.query(Person.phantom_name==phantom).fetch()
            if len(possible_persons)==0:
                lonely_phantoms.append(phantom)
            elif possible_persons[0]!=new_person:
                people.append(possible_persons[0])

        template_values = {
                        'new_person':new_person,
                        'people':people,
                        'phantoms':lonely_phantoms
        }

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))





class ResultsPage(webapp2.RequestHandler):

    def get(self):
        first_name = self.request.get('first_name')
        last_name = self.request.get('last_name')
        print first_name,last_name
        
        possible_persons=Person.query(Person.first_name==first_name,Person.last_name==last_name).fetch()     
        
        if len(possible_persons)==0:
            person=Person(first_name=first_name,last_name=last_name)
            person.put()
        else:
            person=possible_persons[0]

        all_phantoms=getAllPhantoms()

        phantoms_dict={}
        for phantom in all_phantoms:
            phantoms_dict[str(phantom.key.id())]=phantom

        unordered_phantoms=phantoms_dict.keys()
        unordered_phantoms.sort()
        ordered_phantoms = unordered_phantoms

        random.seed(person.key.id())
        random.shuffle(ordered_phantoms)
        
        uniquely_shuffled_phantoms=ordered_phantoms
        
        three_phantoms=[]
        for phantom_id in uniquely_shuffled_phantoms:
            phantom=phantoms_dict[phantom_id]

            possible_persons=Person.query(Person.phantom_name.name==phantom.name).fetch()
            
            if len(possible_persons)==0:
                three_phantoms.append(phantom)
            if len(three_phantoms)==3:
                break

        print three_phantoms




        template_values = {
                'person':person,
                'phantoms':three_phantoms
        }
        template = JINJA_ENVIRONMENT.get_template('results.html')
        self.response.write(template.render(template_values))


class AdminPage(webapp2.RequestHandler):

    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('admin.html')
        self.response.write(template.render(template_values))



class FormPage(webapp2.RequestHandler):

    def get(self):
        template_values = {}
        template = JINJA_ENVIRONMENT.get_template('form.html')
        self.response.write(template.render(template_values))




app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/form', FormPage),
    ('/admin', AdminPage),
    ('/results', ResultsPage),
], debug=True)