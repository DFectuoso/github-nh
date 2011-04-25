#!/usr/bin/env python
from google.appengine.ext import webapp, db
from google.appengine.api import taskqueue
from google.appengine.ext.webapp import util, template

from libs.github import github

import logging
import urllib2
import simplejson

# Models

class Profile(db.Model):
  nh_user     = db.StringProperty(required=True)
  github_user = db.StringProperty(required=False)

  @staticmethod
  def get_or_put_for_nh_user(nh_user):
    profile = Profile.all().filter("nh_user",nh_user).get()
    if profile:
      return profile
    else:
      p = Profile(nh_user=nh_user)
      p.put()
      return p

class Repository(db.Model):
  url         = db.StringProperty()
  #homepage    = db.StringProperty()
  name        = db.StringProperty()
  profile     = db.ReferenceProperty(Profile, collection_name="repos")
  #description = db.StringProperty()
  #open_issues = db.BooleanProperty()
  #has_issues  = db.BooleanProperty()
  #pushed_at   = db.DateTimeProperty()
  #created_at  = db.DateTimeProperty()
  #watchers    = db.IntegerProperty()
  #forks       = db.IntegerProperty()

  @staticmethod
  def get_or_put_by_url(url):
    repo = Repository.all().filter("url",url).get()
    if repo:
      return repo
    else:
      repo = Repository(url=url)
      repo.put()
      return repo

class GetNhUsersHandler(webapp.RequestHandler):
  def get(self):
    url = "http://www.noticiashacker.com/api/usuarios/github"
    try:
      result = urllib2.urlopen(url) 
      users = simplejson.load(result)
      for user in users["github_users"]:
        for nh_user, github_user in user.iteritems():
          p = Profile.get_or_put_for_nh_user(nh_user)
          if p.github_user != github_user:
            p.github_user = github_user
            p.put() 
      self.response.out.write("Ok") 
    except urllib2.URLError,e:
      logging.error("The github users nh api didn't answer") 
      return

class GetGithubInfoHandler(webapp.RequestHandler):
  def get(self):
    profiles = Profile.all()
    for profile in profiles:
      taskqueue.add(url='/tasks/get_github_info_for_user', params={'id': str(profile.key().id())})
    
class GetGithubInfoForUserHandler(webapp.RequestHandler):
  def get(self):
    self.post()

  def post(self):
    profile = Profile.get_by_id(int(self.request.get("id")))
    gh = github.GitHub()
    repos = gh.repos.forUser(profile.github_user)
    for r in repos:
      repo = Repository.get_or_put_by_url(r.url)
      repo.profile = profile
      repo.url = r.url
      repo.name = r.name
      repo.put()

      #repo.description = r.description
      #open_issues = db.BooleanProperty()
      #has_issues  = db.BooleanProperty()
      #pushed_at   = db.DateTimeProperty()
      #created_at  = db.DateTimeProperty()
      #watchers    = db.IntegerProperty()
      #forks       = db.IntegerProperty()

    logging.info("I am in the tasks /get_github_info_for_user with user:" + profile.nh_user) 

class MainHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/main.html', locals()))

class ProfilesHandler(webapp.RequestHandler):
  def get(self):
    profiles = Profile.all()
    self.response.out.write(template.render('templates/profiles.html', locals()))

class RepositoriesHandler(webapp.RequestHandler):
  def get(self, profile_id):
    profile = Profile.get_by_id(int(profile_id))
    repositories = profile.repos
    self.response.out.write(template.render('templates/repositories.html', locals()))

def main():
  application = webapp.WSGIApplication([
      ('/', MainHandler),
      ('/profiles', ProfilesHandler),
      ('/repositories/(.+)', RepositoriesHandler),
      ('/tasks/get_nh_users', GetNhUsersHandler),
      ('/tasks/get_github_info', GetGithubInfoHandler),
      ('/tasks/get_github_info_for_user', GetGithubInfoForUserHandler),
  ], debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
